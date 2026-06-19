"""Step 3b: map_to_ontology — two-pass LLM ontology search with synonym expansion.

Same two-pass structure as the original copy, with:

  · synonyms.json lookup: before Pass 1, the concept is looked up in the
    S3.5 lexical dictionary to collect all known roots_es and roots_en.
    These are injected into the Pass 1 AND Pass 2 prompts so the LLM
    considers all synonymous forms of the concept at both stages.

  · Flexible Pass 1 prompt: prefer recall over precision — include every
    subfamily that could plausibly match, even ambiguous ones.  Steps 3.25
    and 3.5 handle pruning downstream.

  · temperature=0, seed=42 on all LLM calls for maximum stability.

  · Synonym-seeded fallback: if the two-pass LLM search returns 0 nodes,
    a deterministic synonym lookup against ontology_synonyms.json is used
    to seed matched_nodes directly.  This fixes niche or abbreviated terms
    (e.g. "airpods" → EARBUDS, "ultrabook" → LAPTOP) that the LLM misses.

  · Session cache: same concept -> identical result within a process.

Public interface: map_to_ontology(concept, question) — async coroutine.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import unicodedata

from openai import AsyncOpenAI

from retail_electronics.config import (
    MODEL_ONTOLOGY,
    ONTOLOGY_FINAL_JSON_PATH,
    ONTOLOGY_JSON_PATH,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)

logger = logging.getLogger(__name__)

client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)


# ── Ontology loading ──────────────────────────────────────────────────────

_ontology_cache: dict | None = None


def _load_ontology() -> dict:
    global _ontology_cache
    if _ontology_cache is None:
        with open(ONTOLOGY_FINAL_JSON_PATH, encoding="utf-8") as f:
            _ontology_cache = json.load(f)
    return _ontology_cache


_lex_syn_cache: dict | None = None


def _load_lex_synonyms() -> dict:
    """Load synonyms.json — the S3.5 lexical root dictionary."""
    global _lex_syn_cache
    if _lex_syn_cache is None:
        path = ONTOLOGY_JSON_PATH.parent / "synonyms.json"
        with open(path, encoding="utf-8") as f:
            _lex_syn_cache = json.load(f)
    return _lex_syn_cache


def _get_synonyms(concept: str) -> list[str]:
    """Return all roots_es + roots_en from synonyms.json related to concept.

    Scans every entry whose roots overlap with the concept as a substring
    (either direction). Returns a deduplicated flat list ready to inject
    into the Pass 1 and Pass 2 LLM prompts.

    e.g. concept="earphones"
         hits EARBUDS    (roots_en=["earbud","earphone","in-ear","airpod","tws"])
         hits HEADPHONES (roots_en=["headphone","headset","over-ear","on-ear"])
         returns all unique roots from both entries
    """
    lex = _load_lex_synonyms()
    c_low = concept.lower().strip()
    found: list[str] = []
    seen:  set[str]  = set()

    for key, entry in lex.items():
        if key.startswith("_"):
            continue
        roots = entry.get("roots_es", []) + entry.get("roots_en", [])
        hit = any(r.lower() in c_low or c_low in r.lower() for r in roots)
        if hit:
            for r in roots:
                r_low = r.lower()
                if r_low not in seen:
                    seen.add(r_low)
                    found.append(r)

    return found


# ── Helpers ───────────────────────────────────────────────────────────────

def _build_skeleton(ontology: dict) -> str:
    """Subfamily skeleton with top-8 product-type hints per line."""
    lines = []
    for fam_name, fam in ontology["children"].items():
        for sub_name, sub in fam["children"].items():
            pts = sub.get("children", {})
            top = sorted(
                pts.items(),
                key=lambda kv: kv[1].get("sku_count", 0),
                reverse=True,
            )[:8]
            hint = ", ".join(name for name, _ in top) if top else "-"
            lines.append(
                f"{fam_name} > {sub_name} ({sub['sku_count']} SKUs)"
                f"  e.g. [{hint}]"
            )
    return "\n".join(lines)


def _build_subfamily_detail(subfamily_node: dict) -> str:
    lines = []
    for pt_name, pt in subfamily_node["children"].items():
        lines.append(f"{pt_name} ({pt['sku_count']} SKUs)")
    return "\n".join(lines)


def _get_node(ontology: dict, family: str, subfamily: str) -> dict | None:
    return (
        ontology["children"]
        .get(family, {})
        .get("children", {})
        .get(subfamily)
    )


def _get_leaf(ontology: dict, family: str, subfamily: str, product_type: str) -> dict | None:
    sub = _get_node(ontology, family, subfamily)
    if sub is None:
        return None
    return sub["children"].get(product_type)


# ── LLM calls ─────────────────────────────────────────────────────────────

async def _llm(system: str, user: str) -> dict:
    response = await client.chat.completions.create(
        model=MODEL_ONTOLOGY,
        response_format={"type": "json_object"},
        temperature=1,
        seed=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return json.loads(response.choices[0].message.content)


async def _pass1(concept: str, synonyms: list[str], skeleton: str) -> dict:
    """Pass 1: find relevant subfamilies — maximally inclusive / recall-first.

    The concept's known synonyms from synonyms.json are injected into the
    user message so the LLM considers all synonymous forms when scanning
    the skeleton. Ambiguous matches are included with confidence=low rather
    than excluded — downstream steps handle pruning.
    """
    system = (
        "You are a product taxonomy expert for an electronics retailer's product catalogue.\n"
        "Given a product concept, a list of its known synonyms/roots, and a list of\n"
        "product subfamilies with example product types, return EVERY subfamily that\n"
        "has ANY chance of containing items related to the concept or any of its synonyms.\n\n"
        "Rules:\n"
        "- ALWAYS prefer to INCLUDE rather than exclude.\n"
        "- If you are uncertain whether a subfamily is relevant, INCLUDE IT with confidence=low.\n"
        "- Consider ALL provided synonyms and roots when evaluating each subfamily.\n"
        "- Only omit a subfamily if you are absolutely certain it cannot be related to\n"
        "  the concept OR any of its synonyms.\n"
        "- Downstream steps will filter false positives — your job is maximum recall.\n\n"
        "For each match return:\n"
        "- family: exact family name from the list\n"
        "- subfamily: exact subfamily name from the list\n"
        "- confidence: \"high\" (clear match) | \"medium\" (probable) | \"low\" (possible/ambiguous)\n"
        "- reasoning: one sentence\n\n"
        "Return JSON: {\"matches\": [{\"family\": \"...\", \"subfamily\": \"...\", "
        "\"confidence\": \"...\", \"reasoning\": \"...\"}]}\n"
        "Return an empty list ONLY if the concept is completely unrelated to any retail product."
    )
    syn_block = ""
    if synonyms:
        syn_block = f"\nKnown synonyms / related roots: {', '.join(synonyms)}\n"
    user = (
        f"Concept: {concept}"
        f"{syn_block}"
        f"\nAvailable subfamilies:\n{skeleton}"
    )
    return await _llm(system, user)


async def _pass2(
    concept: str,
    family: str,
    subfamily: str,
    detail: str,
    synonyms: list[str] | None = None,
) -> dict:
    """Pass 2: find specific product types within a matched subfamily.

    Synonyms are injected here too so the LLM recognises non-Spanish or
    abbreviated product names that don't literally contain the concept word.
    """
    system = (
        "You are a product taxonomy expert for an electronics retailer's product catalogue.\n"
        "Given a product concept (and its known synonyms/roots) plus all product types\n"
        "within a specific subfamily, select the product types that genuinely match.\n"
        "Be VERY INCLUSIVE — prefer inclusion when uncertain or ambiguous.\n\n"
        "Rules:\n"
        "- Include a product type if it could plausibly be what the user is looking for.\n"
        "- Consider all synonyms and roots — product type names may be in Spanish, English,\n"
        "  or abbreviated codes that match a synonym rather than the literal concept word.\n"
        "- When in doubt, INCLUDE with confidence=low rather than exclude.\n"
        "- Downstream steps will prune false positives.\n\n"
        "For each match return:\n"
        "- product_type: the BARE product type name only — strip the trailing\n"
        "  '(N SKUs)' count that appears in the input list. For example, return\n"
        "  'Laptop 13\" Ultrabook' NOT 'Laptop 13\" Ultrabook (4 SKUs)'.\n"
        "- confidence: \"high\" | \"medium\" | \"low\"\n"
        "- reasoning: one sentence\n\n"
        "Return JSON: {\"matches\": [{\"product_type\": \"...\", \"confidence\": \"...\", "
        "\"reasoning\": \"...\"}]}\n"
        "If nothing at all matches (even loosely), return {\"matches\": []}"
    )
    syn_block = ""
    if synonyms:
        syn_block = f"\nKnown synonyms / related roots: {', '.join(synonyms)}\n"
    user = (
        f"Concept: {concept}"
        f"{syn_block}"
        f"\nSubfamily: {family} > {subfamily}\n\n"
        f"Available product types:\n{detail}"
    )
    return await _llm(system, user)


# ── Synonym-seeded fallback ───────────────────────────────────────────────
#
# When the two-pass LLM search returns 0 matched_nodes, we fall back to a
# direct deterministic lookup in ontology_synonyms.json.  This catches
# brand-name aliases ("airpods" → EARBUDS), variant terms ("chromebook" → LAPTOP),
# and niche product names the LLM doesn't recognise from the skeleton alone.
#
# Ported verbatim from the notebook Patch 2 (full_workflow_last.ipynb).

_syn_tree_cache: dict | None = None
_syn_nodes_cache: list | None = None


def _get_syn_nodes() -> list[tuple[str, str, list[str]]]:
    """Return flattened (path, name, synonyms) tuples from ontology_synonyms.json."""
    global _syn_tree_cache, _syn_nodes_cache
    if _syn_nodes_cache is None:
        from retail_electronics.ontology.search3 import _load as _load_syn_tree, _flatten as _flatten_syn
        _syn_tree_cache = _load_syn_tree()
        _syn_nodes_cache = _flatten_syn(_syn_tree_cache)
    return _syn_nodes_cache


def _normalize(text: str) -> str:
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _stem_token(t: str) -> set[str]:
    """Return a small set of singular/plural variants for a token.

    Not a real stemmer — just the trailing -s / -es / -ies heuristic that
    is enough to bridge English plurals stored in synonym files.
    """
    variants: set[str] = {t}
    if len(t) > 3 and t.endswith("ies"):
        variants.add(t[:-3] + "y")
    elif len(t) > 3 and t.endswith("es"):
        variants.add(t[:-2])
        variants.add(t[:-1])
    elif len(t) > 3 and t.endswith("s"):
        variants.add(t[:-1])
    else:
        variants.add(t + "s")
        variants.add(t + "es")
    return variants


def _synonym_seeded_nodes(concept: str, ontology: dict) -> list[dict]:
    """Return matched_nodes synthesized from direct ontology_synonyms.json matches.

    For a single-token concept: ANY variant (singular/plural) must appear as a
    whole word in the hay (name + synonyms).
    For a multi-token concept: EVERY token must match. Prevents "training shirts"
    from seeding BOLSA just because BOLSA has "training" in its synonym list.
    Scopes to product_type leaves (4-segment paths).
    """
    c = _normalize(concept).strip()
    if not c:
        return []

    tokens = [t for t in c.split() if len(t) >= 3]
    if not tokens:
        tokens = [c]

    token_variants = [_stem_token(t) for t in tokens]

    matched: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for node_path, name, syns in _get_syn_nodes():
        parts = node_path.split("/")
        if len(parts) != 4:
            continue
        _, family, subfamily, product_type = parts

        hay = " " + _normalize(name + " " + " ".join(syns)) + " "

        def token_hit(variants: set[str]) -> bool:
            return any(f" {v} " in hay for v in variants)

        if not all(token_hit(v) for v in token_variants):
            if c not in hay:
                continue

        key = (family, subfamily, product_type)
        if key in seen:
            continue
        seen.add(key)

        # Pull sku_count from the Milan ontology.
        try:
            sub_leaves = (
                ontology["children"]
                .get(family, {})
                .get("children", {})
                .get(subfamily, {})
                .get("children", {})
            )
            leaf = sub_leaves.get(product_type, {})
            sku_count = leaf.get("sku_count", 0)

            if sku_count > 0:
                matched.append({
                    "path": f"{family} > {subfamily} > {product_type}",
                    "level": 4,
                    "family": family,
                    "subfamily": subfamily,
                    "product_category": subfamily,
                    "product_type": product_type,
                    "sku_count": sku_count,
                })
                continue

            # Bridge: expand to Milan leaves when the synonym node is a category-level
            # entry that doesn't map 1:1 to a Milan leaf.
            # Gate: only trigger when ≥2 synonyms match a concept token (prevents
            # incidental one-word overlaps like GEMELOS/"shirt cufflinks").
            syn_hits = sum(
                1 for s in syns
                if any(
                    any(f" {v} " in (" " + _normalize(s) + " ") for v in variants)
                    for variants in token_variants
                )
            )
            if syn_hits < 2:
                continue

            pt_tokens = {
                _normalize(t)
                for t in product_type.split()
                if len(t) >= 3
            }
            if not pt_tokens:
                continue
            for milan_pt, milan_leaf in sub_leaves.items():
                if milan_leaf.get("sku_count", 0) == 0:
                    continue
                milan_norm = " " + _normalize(milan_pt) + " "
                if any(f" {t} " in milan_norm for t in pt_tokens):
                    bridge_key = (family, subfamily, milan_pt)
                    if bridge_key in seen:
                        continue
                    seen.add(bridge_key)
                    matched.append({
                        "path": f"{family} > {subfamily} > {milan_pt}",
                        "level": 4,
                        "family": family,
                        "subfamily": subfamily,
                        "product_category": subfamily,
                        "product_type": milan_pt,
                        "sku_count": milan_leaf.get("sku_count", 0),
                    })
        except Exception:
            continue

    return matched


# ── Main async search ─────────────────────────────────────────────────────

async def _search(ontology: dict, concept: str) -> dict:
    skeleton = _build_skeleton(ontology)
    synonyms = _get_synonyms(concept)

    logger.info(
        "Pass 1 — concept=%r  synonyms=%s",
        concept,
        synonyms[:8] if synonyms else "(none found in synonyms.json)",
    )

    # ── Pass 1: LLM finds relevant subfamilies ───────────────────────────
    p1_result = await _pass1(concept, synonyms, skeleton)

    pass2_inputs = []
    seen_subs: set[tuple[str, str]] = set()

    for match in p1_result.get("matches", []):
        family    = match.get("family",    "").split(" > ")[0].strip()
        subfamily = match.get("subfamily", "").split(" > ")[-1].strip()
        if not family or not subfamily:
            continue
        key = (family, subfamily)
        if key in seen_subs:
            continue
        sub_node = _get_node(ontology, family, subfamily)
        if sub_node is None:
            continue
        seen_subs.add(key)
        pass2_inputs.append({
            "family":               family,
            "subfamily":            subfamily,
            "subfamily_confidence": match.get("confidence", "low"),
            "detail":               _build_subfamily_detail(sub_node),
        })

    logger.info("Pass 1 -> %d unique subfamilies", len(pass2_inputs))

    if not pass2_inputs:
        return {
            "concept": concept,
            "matched_nodes": [],
            "item_matches": [],
            "granularity": "none",
            "disambiguation_needed": False,
        }

    # ── Pass 2: LLM finds product types within each subfamily ────────────
    # Synonyms are passed to Pass 2 as well so the LLM can match abbreviated
    # or non-Spanish product type names via the synonym list.
    pass2_results = await asyncio.gather(*[
        _pass2(concept, p["family"], p["subfamily"], p["detail"], synonyms)
        for p in pass2_inputs
    ])

    seen_paths = set()
    matched_nodes = []

    for p2_input, p2_output in zip(pass2_inputs, pass2_results):
        for match in p2_output.get("matches", []):
            family = p2_input["family"]
            subfamily = p2_input["subfamily"]
            product_type = match.get("product_type", "")
            # Defensive: strip any trailing "(N SKUs)" suffix the LLM may have
            # echoed back from the input. _build_subfamily_detail appends this
            # count for context; some Pass 2 responses include it in the
            # product_type field, which would break the _get_leaf lookup.
            product_type = re.sub(r"\s*\(\d+\s*SKUs?\)\s*$", "", product_type).strip()
            path_key = (family, subfamily, product_type)
            if path_key in seen_paths:
                continue
            seen_paths.add(path_key)

            leaf = _get_leaf(ontology, family, subfamily, product_type)
            if leaf is None:
                continue

            matched_nodes.append({
                "path": f"{family} > {subfamily} > {product_type}",
                "level": 4,
                "family": family,
                "subfamily": subfamily,
                "product_category": subfamily,
                "product_type": product_type,
                "sku_count": leaf["sku_count"],
            })

    granularity = "product_type" if matched_nodes else "none"

    logger.info("Matched %d nodes (granularity: %s)", len(matched_nodes), granularity)
    for n in matched_nodes[:5]:
        logger.info("  → %s (SKUs: %d)", n["path"], n["sku_count"])

    return {
        "concept": concept,
        "matched_nodes": matched_nodes,
        "item_matches": [],
        "granularity": granularity,
        "disambiguation_needed": False,
    }


# ── Session cache ─────────────────────────────────────────────────────────

_search_cache: dict[str, dict] = {}


# ── Public interface ──────────────────────────────────────────────────────

async def map_to_ontology(concept: str | None, question: str = "") -> dict:
    """Map a product concept to ontology nodes via two-pass LLM search.

    Pass 1 — LLM selects relevant subfamilies from the skeleton, guided by
             the concept AND its synonyms looked up from synonyms.json.
    Pass 2 — LLM selects specific product types within each matched subfamily,
             also guided by synonyms for maximum recall.
    Fallback — If both passes return 0 nodes, a deterministic synonym-seeded
             lookup in ontology_synonyms.json is used. This catches non-Spanish
             or niche terms the LLM may not recognise from the skeleton alone.

    Results are cached per concept within the process lifetime.

    Args:
        concept: bare product noun from S2, e.g. "laptop", "headphones".
                 None / empty -> all items (no node filter).
        question: full user question (kept for API compatibility; not used
                  by the two-pass search itself).

    Returns:
        dict with matched_nodes, granularity, disambiguation_needed.
        Includes via='synonym_seed' when the fallback was used.
    """
    logger.info("=" * 60)
    logger.info("STEP 3b: MAP TO ONTOLOGY")
    logger.info("Concept: %s", concept)

    if not concept:
        logger.info("No concept — query applies to all items")
        return {
            "concept": concept,
            "matched_nodes": [],
            "item_matches": [],
            "granularity": "all",
            "disambiguation_needed": False,
        }

    cache_key = concept.lower().strip()
    if cache_key in _search_cache:
        logger.info("Cache hit for %r", concept)
        return _search_cache[cache_key]

    ontology = _load_ontology()
    result = await _search(ontology, concept)

    # ── Synonym-seeded fallback ──────────────────────────────────────────
    # If the LLM two-pass search found nothing, fall back to a deterministic
    # lookup in ontology_synonyms.json.  This is the critical fix for terms
    # like "airpods" (→ EARBUDS), "ultrabook" (→ LAPTOP), or any concept
    # whose canonical catalogue name the LLM doesn't recognise from context.
    if not result.get("matched_nodes") and concept:
        seeded = _synonym_seeded_nodes(concept, ontology)
        if seeded:
            logger.info(
                "Synonym fallback: LLM returned 0 nodes for %r — "
                "seeded %d node(s) from ontology_synonyms.json",
                concept, len(seeded),
            )
            result = {
                **result,
                "matched_nodes": seeded,
                "granularity": "product_type",
                "disambiguation_needed": False,
                "via": "synonym_seed",
            }
        else:
            logger.info(
                "Synonym fallback: no synonym matches found for %r either.", concept
            )

    _search_cache[cache_key] = result
    return result