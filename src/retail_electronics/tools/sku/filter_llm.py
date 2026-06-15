"""Step 3.5: sku_filter — LLM-based SKU relevance filter.

Two paths, selected automatically based on cardinality:

  Path A — lexical + LLM  : lexical pre-filter reduces the item pool, then
                             the LLM classifies remaining (cryptic/abbreviated)
                             items. Used when unique signatures > _LLM_ALL_SIG_THRESHOLD.
                             Efficient for large concepts (e.g. all COMPUTING/Laptops).

  Path B — LLM-all        : sends ALL unique product signatures directly to the
                             LLM for classification in a single call. Used when
                             unique signatures ≤ _LLM_ALL_SIG_THRESHOLD.
                             Resolves both failure modes that lexical cannot handle:
                               · False positives: "Headphone-Print Phone Case" when
                                 asking about headphones — lexical passes it, LLM rejects it.
                               · False negatives: "G17-1TB-RGB" when asking about
                                 gaming laptops — lexical rejects it, LLM recovers it.

Selection logic (automatic, no user configuration needed):
  unique_sigs ≤ _LLM_ALL_SIG_THRESHOLD → Path B (LLM-all)
  unique_sigs >  _LLM_ALL_SIG_THRESHOLD → Path A (lexical + LLM)

filter_lexical is kept as an internal helper for Path A.

Public entry point: sku_filter(concept, matched_nodes, question="")
"""

from __future__ import annotations

import json
import logging
import re
import time
import unicodedata

from retail_electronics.config import (
    MODEL_SKU_FILTER,
    ONTOLOGY_FINAL_JSON_PATH,
    SYNONYMS_PATH,
)
from retail_electronics.llm.client import chat_json

logger = logging.getLogger(__name__)

# Path A: max items per LLM batch for the lexical+LLM path.
_LLM_BATCH_SIZE = 80

# Path B threshold: if unique product signatures across all matched nodes is ≤ this,
# skip lexical entirely and send everything to the LLM for direct classification.
# Data shows P99 of single-node sig counts is 126; most realistic multi-node
# queries stay well under 150. Only very broad concepts ("all textil general")
# exceed this and benefit from the lexical pre-filter of Path A.
_LLM_ALL_SIG_THRESHOLD = 10000

# ── Data loading ──────────────────────────────────────────────────────

_synonyms_cache: dict | None = None
_ontology_cache: dict | None = None


def _load_synonyms() -> dict:
    global _synonyms_cache
    if _synonyms_cache is None:
        with open(SYNONYMS_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        _synonyms_cache = {k: v for k, v in raw.items() if not k.startswith("_")}
    return _synonyms_cache


def _load_ontology() -> dict:
    global _ontology_cache
    if _ontology_cache is None:
        with open(ONTOLOGY_FINAL_JSON_PATH, encoding="utf-8") as f:
            _ontology_cache = json.load(f)
    return _ontology_cache


# ── Item extraction ───────────────────────────────────────────────────

def _get_items_for_nodes(ontology: dict, matched_nodes: list[dict]) -> list[dict]:
    """Return all item strings from the product_type leaves of matched_nodes."""
    items: list[dict] = []
    for node in matched_nodes:
        family = node.get("family", "")
        subfamily = node.get("subfamily", "")
        product_type = node.get("product_type", "")
        try:
            pt_node = (
                ontology["children"]
                .get(family, {})
                .get("children", {})
                .get(subfamily, {})
                .get("children", {})
                .get(product_type, {})
            )
            for item_str in pt_node.get("items", []):
                items.append({
                    "item_str": item_str,
                    "family": family,
                    "subfamily": subfamily,
                    "product_type": product_type,
                })
        except Exception:
            pass
    return items


# ── Concept → roots lookup ────────────────────────────────────────────

def _normalize(text: str) -> str:
    """Lowercase and strip combining accents."""
    nfkd = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _get_roots(concept: str, synonyms: dict) -> tuple[list[str], list[str]]:
    """Return (roots_es, roots_en) for a concept via synonyms.json lookup.

    Strategy (in order):
      1. Direct key match   — concept contains a synonyms key (e.g. "earbuds" → EARBUDS)
      2. Best-overlap match — concept words overlap most with a key's roots
      3. Fallback           — use concept words themselves as roots

    Defensive: entries may have only roots_en (electronics) or only roots_es
    (legacy) — both lookups use .get() with empty-list fallback.
    """
    concept_norm = _normalize(concept)

    # 1. Direct key match
    for key, val in synonyms.items():
        if _normalize(key) in concept_norm:
            logger.debug("Roots: direct key match '%s'", key)
            return val.get("roots_es", []), val.get("roots_en", [])

    # 2. Best-overlap match
    best_key: str | None = None
    best_score = 0
    for key, val in synonyms.items():
        candidates = [_normalize(r) for r in val.get("roots_es", []) + val.get("roots_en", []) + [key]]
        score = sum(
            1
            for word in concept_norm.split()
            if any(word in cand or cand in word for cand in candidates)
        )
        if score > best_score:
            best_score = score
            best_key = key

    if best_key and best_score > 0:
        logger.debug("Roots: overlap match '%s' (score=%d)", best_key, best_score)
        return synonyms[best_key].get("roots_es", []), synonyms[best_key].get("roots_en", [])

    # 3. Fallback
    logger.debug("Roots: fallback — using concept words as roots")
    words = concept_norm.split()
    return words, words


# ── Path A — Lexical filter ───────────────────────────────────────────

def _matches_roots(item_str: str, roots_es: list[str], roots_en: list[str]) -> bool:
    item_norm = _normalize(item_str)
    return any(_normalize(root) in item_norm for root in roots_es + roots_en)


def filter_lexical(
    concept: str,
    items: list[dict],
) -> tuple[list[dict], list[dict], dict]:
    """Path A: deterministic substring-root filter.

    Returns:
        matched  — items whose item_str contains at least one root
        rejected — items that did not match any root
        meta     — roots used and timing
    """
    t0 = time.perf_counter()
    synonyms = _load_synonyms()
    roots_es, roots_en = _get_roots(concept, synonyms)

    logger.info("Lexical roots — ES: %s | EN: %s", roots_es, roots_en)

    matched, rejected = [], []
    for item in items:
        if _matches_roots(item["item_str"], roots_es, roots_en):
            matched.append(item)
        else:
            rejected.append(item)

    elapsed = round(time.perf_counter() - t0, 4)
    logger.info("Lexical: %d/%d kept in %.4fs", len(matched), len(items), elapsed)
    return matched, rejected, {"roots_es": roots_es, "roots_en": roots_en, "time_s": elapsed}


# ── Size filter ──────────────────────────────────────────────────────

# ── Path C — LLM recovery (gpt-4o-mini via shared client) ────────────

def _product_sig(item_str: str) -> str:
    """Strip a trailing parenthesized token to get a unique product signature.

    Electronics item names typically have no trailing (TOKEN), so this returns
    the input unchanged for the current catalogue. Kept for catalogues that
    encode size/variant in a trailing parenthesis.
    """
    return re.sub(r"\s*\([^)]+\)\s*$", "", item_str).strip()


def _dedup_signatures(items: list[dict]) -> tuple[list[dict], dict[str, list[dict]]]:
    """Collapse size variants into unique product signatures.

    Returns:
        unique_items   — one representative dict per unique (node_path, sig)
        sig_to_items   — mapping from sig → all original item dicts with that sig
                         (used to expand the LLM's keep list back to full SKUs)
    """
    sig_to_items: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    unique_items: list[dict] = []

    for item in items:
        sig = _product_sig(item["item_str"])
        key = (item["family"], item["subfamily"], item["product_type"], sig)
        sig_to_items.setdefault(sig, []).append(item)
        if key not in seen:
            seen.add(key)
            unique_items.append({**item, "sig": sig})

    return unique_items, sig_to_items


def _llm_recover(
    concept: str,
    question: str,
    ambiguous: list[dict],
) -> list[dict]:
    """Path C helper: recover relevant items from the lexically-rejected pool.

    Used only when unique sigs > _LLM_ALL_SIG_THRESHOLD and lexical has already
    run as a pre-filter. The LLM only sees items that lexical could not classify.

    Args:
        concept   — canonical product concept, e.g. "headphones"
        question  — full user question for context
        ambiguous — items lexical rejected

    Returns:
        list of item dicts recovered by the LLM (all size variants expanded)
    """
    if not ambiguous:
        return []

    unique_items, sig_to_items = _dedup_signatures(ambiguous)
    logger.info(
        "LLM recover — %d ambiguous items → %d unique signatures",
        len(ambiguous), len(unique_items),
    )

    recovered_sigs: set[str] = set()

    for batch_start in range(0, len(unique_items), _LLM_BATCH_SIZE):
        batch = unique_items[batch_start: batch_start + _LLM_BATCH_SIZE]

        numbered = "\n".join(
            f"{i + 1}. [{it['family']} > {it['subfamily']} > {it['product_type']}] {it['sig']}"
            for i, it in enumerate(batch)
        )

        prompt = (
            f"You are filtering a retail product catalogue.\n\n"
            f'User question: "{question}"\n'
            f'Product concept: "{concept}"\n\n'
            f"The items below were NOT matched by keyword filtering — their names "
            f"are cryptic, abbreviated, or use internal model codes. "
            f"Each item shows its ontology path [Family > Subfamily > Type].\n\n"
            f"Decide which items correspond to what the user is asking about.\n"
            f"When in doubt, include the item — missing a genuine match is worse "
            f"than including a borderline one.\n\n"
            f"Items:\n{numbered}\n\n"
            f'Return JSON with a single key "keep" listing the numbers to include.\n'
            f'Example: {{"keep": [1, 3, 5]}}\n'
            f'If none are relevant: {{"keep": []}}'
        )

        try:
            result = chat_json(prompt, model=MODEL_SKU_FILTER, temperature=0)
            keep_nums = set(result.get("keep", []))
            for idx in keep_nums:
                if 1 <= idx <= len(batch):
                    recovered_sigs.add(batch[idx - 1]["sig"])
        except Exception as e:
            logger.warning(
                "LLM batch %d–%d failed: %s — skipping",
                batch_start + 1, batch_start + len(batch), e,
            )

    recovered: list[dict] = []
    for sig in recovered_sigs:
        recovered.extend(sig_to_items.get(sig, []))

    logger.info("LLM recovered %d signatures → %d items", len(recovered_sigs), len(recovered))
    return recovered


# ── Path B — LLM-all classifier ───────────────────────────────────────

# Few-shot examples embedded in every Path-B prompt.
# They anchor the two failure modes the lexical filter cannot handle:
#   1. False positives: item contains the concept word but is a different product.
#   2. False negatives: item IS the concept but uses a cryptic name or code.
_FEW_SHOTS = """\
Examples of correct decisions:

Question: "How many headphones were sold?"
1. [AUDIO > Headphones > Studio Headphones] Studio Reference Headphones BLACK
   → RELEVANT: genuine headphones.
2. [MOBILE > Phone Cases > Silicone Case] Headphone-Print Silicone Case BLACK
   → NOT RELEVANT: "Headphone" appears in the name but the path reveals it's a phone case.
3. [SMART HOME > Smart Lighting > Smart Lamp Desk] Headphone-Shaped Smart Lamp WHITE
   → NOT RELEVANT: a desk lamp shaped like headphones, not actual headphones.

Question: "How many gaming laptops were sold?"
4. [COMPUTING > Laptops > Laptop 17" Gaming] G17-1TB-RGB BLACK
   → RELEVANT: cryptic SKU code but the path Laptops > Laptop 17" Gaming confirms it.
5. [COMPUTING > Laptops > Laptop 13" Ultrabook] Laptop 13" Ultrabook 16GB/512GB SILVER
   → NOT RELEVANT: ultrabook, not a gaming laptop.
"""


def filter_llm_all(
    concept: str,
    question: str,
    items: list[dict],
) -> dict:
    """Path B: classify ALL items directly with the LLM in a single call.

    Used when unique product signatures ≤ _LLM_ALL_SIG_THRESHOLD. Skips the
    lexical filter entirely, resolving both failure modes it cannot handle:

      - False positives: "Headphone-Print Silicone Case" contains "headphone"
        but is a phone case → lexical would pass it, LLM correctly rejects it.
      - False negatives: "G17-1TB-RGB" IS a gaming laptop but has no recognisable
        root → lexical would reject it, LLM correctly includes it.

    The LLM receives the full ontology path per item (primary signal) plus few-shot
    examples of both failure modes for consistent behaviour across concepts.

    On LLM failure, falls back to returning all items (safe recall guarantee).

    Args:
        concept  — product concept, e.g. "headphones"
        question — full user question
        items    — all item dicts from matched_nodes

    Returns:
        result dict compatible with filter_hybrid output schema.
    """
    t0 = time.perf_counter()

    if not items:
        return {
            "matched": [], "path": "B",
            "total_input": 0, "total_matched": 0,
            "matched_by_lexical": 0, "sent_to_llm": 0, "recovered_by_llm": 0,
            "time_lexical_s": 0.0, "time_llm_s": 0.0,
            "roots_es": [], "roots_en": [],
        }

    unique_items, sig_to_items = _dedup_signatures(items)
    n_sigs = len(unique_items)
    logger.info("LLM-all — %d items → %d unique sigs to classify", len(items), n_sigs)

    numbered = "\n".join(
        f"{i + 1}. [{it['family']} > {it['subfamily']} > {it['product_type']}] {it['sig']}"
        for i, it in enumerate(unique_items)
    )

    prompt = (
        f"You are filtering a retail product catalogue.\n\n"
        f"{_FEW_SHOTS}\n"
        f"---\n\n"
        f"Now classify these items for the query below.\n\n"
        f'User question: "{question}"\n'
        f'Product concept: "{concept}"\n\n'
        f"Each item shows its ontology path [Family > Subfamily > Type] followed "
        f"by its product name. Use the path as primary signal — if the Type "
        f"clearly matches the concept, include it even if the name is cryptic. "
        f"If the name reveals a clearly different product type, exclude it. "
        f"When genuinely unsure, include the item.\n\n"
        f"Items:\n{numbered}\n\n"
        f'Return JSON with a single key "keep" listing the item numbers to include.\n'
        f'Example: {{"keep": [1, 2, 4]}}\n'
        f'If none are relevant: {{"keep": []}}'
    )

    kept_sigs: set[str] = set()
    try:
        result = chat_json(prompt, model=MODEL_SKU_FILTER, temperature=0)
        keep_nums = set(result.get("keep", []))
        for idx in keep_nums:
            if 1 <= idx <= n_sigs:
                kept_sigs.add(unique_items[idx - 1]["sig"])
        logger.info("LLM-all kept %d/%d sigs", len(kept_sigs), n_sigs)
    except Exception as e:
        logger.warning("LLM-all call failed: %s — falling back to all items", e)
        kept_sigs = {it["sig"] for it in unique_items}

    matched: list[dict] = []
    for sig in kept_sigs:
        matched.extend(sig_to_items.get(sig, []))

    t_llm = round(time.perf_counter() - t0, 4)
    logger.info("LLM-all: %d/%d items kept in %.4fs", len(matched), len(items), t_llm)

    return {
        "matched": matched,
        "path": "B",
        "total_input": len(items),
        "total_matched": len(matched),
        "matched_by_lexical": 0,
        "sent_to_llm": n_sigs,
        "recovered_by_llm": len(matched),
        "time_lexical_s": 0.0,
        "time_llm_s": t_llm,
        "roots_es": [],
        "roots_en": [],
    }


def filter_hybrid(concept: str, question: str, items: list[dict]) -> dict:
    """Route to Path B (LLM-all) or Path C (lexical + LLM) based on cardinality.

    Path B — unique sigs ≤ _LLM_ALL_SIG_THRESHOLD:
        Send all items directly to the LLM. Resolves both false positives
        (lexical passing noise) and false negatives (lexical missing cryptic names).

    Path A — unique sigs > _LLM_ALL_SIG_THRESHOLD:
        Lexical pre-filter first, then LLM on remaining items only.
        Used for large concepts (e.g. all COMPUTING/Laptops) where sending
        hundreds of sigs to the LLM in one call is impractical.
    """
    # Count unique sigs to decide routing — dedup without sorting to preserve order
    seen_sigs: set[tuple] = set()
    n_unique = 0
    for item in items:
        sig = _product_sig(item["item_str"])
        key = (item["family"], item["subfamily"], item["product_type"], sig)
        if key not in seen_sigs:
            seen_sigs.add(key)
            n_unique += 1

    logger.info(
        "filter_hybrid — %d items, %d unique sigs, threshold=%d → path %s",
        len(items), n_unique, _LLM_ALL_SIG_THRESHOLD,
        "B (llm_all)" if n_unique <= _LLM_ALL_SIG_THRESHOLD else "A (lexical+llm)",
    )

    if n_unique <= _LLM_ALL_SIG_THRESHOLD:
        return filter_llm_all(concept, question, items)

    # Path A: lexical pre-filter + LLM on rejects
    matched_lex, rejected_lex, lex_meta = filter_lexical(concept, items)
    logger.info("Path A stage 1 — lexical: %d kept, %d rejected", len(matched_lex), len(rejected_lex))

    t_llm_start = time.perf_counter()
    recovered_llm = _llm_recover(concept, question, rejected_lex) if rejected_lex else []
    t_llm = round(time.perf_counter() - t_llm_start, 4)
    logger.info("Path A stage 2 — LLM recovered: %d in %.4fs", len(recovered_llm), t_llm)

    all_matched = matched_lex + recovered_llm

    return {
        "matched": all_matched,
        "path": "A",
        "total_input": len(items),
        "total_matched": len(all_matched),
        "matched_by_lexical": len(matched_lex),
        "sent_to_llm": len(rejected_lex),
        "recovered_by_llm": len(recovered_llm),
        "time_lexical_s": lex_meta["time_s"],
        "time_llm_s": t_llm,
        "roots_es": lex_meta["roots_es"],
        "roots_en": lex_meta["roots_en"],
    }


# ── Public entry point ────────────────────────────────────────────────

def sku_filter(
    concept: str,
    matched_nodes: list[dict],
    question: str = "",
    items_override: list[dict] | None = None,
) -> dict:
    """Step 3.5: refine SKUs from matched ontology nodes by concept relevance.

    Automatically routes to Path A (lexical + LLM) or Path B (LLM-all)
    based on the number of unique product signatures in matched_nodes.

    Args:
        concept:        product concept from the user's question (e.g. "headphones")
        matched_nodes:  output from step3b — list of matched ontology node dicts
        question:       full user question for LLM context (e.g.
                        "gaming laptops sold in 2024")
        items_override: optional pre-filtered item pool from Step 3.25
                        (sku_prefilter).  When provided, this list is used
                        instead of re-deriving items from matched_nodes.
                        Allows S3.25 to narrow the pool by size / date range
                        before the expensive LLM pass.

    Returns:
        dict with:
          concept            — original concept
          item_names         — filtered item name strings (ready for Step 4)
          path               — "A" (lexical+LLM) or "B" (LLM-all)
          total_input        — total items before filtering
          total_matched      — items kept after filtering
          matched_by_lexical — items caught by lexical stage (Path A only, else 0)
          sent_to_llm        — unique signatures evaluated by LLM
          recovered_by_llm   — items the LLM kept
          time_lexical_s     — time in lexical filter (0 for Path B)
          time_llm_s         — time in LLM call
          roots_es / roots_en — roots used (Path A only, else empty)
    """
    logger.info("=" * 60)
    logger.info("STEP 3.5: SKU FILTER")
    logger.info("Concept: '%s' | Nodes: %d", concept, len(matched_nodes))

    _empty = {
        "concept": concept, "item_names": [], "path": "B",
        "total_input": 0, "total_matched": 0,
        "matched_by_lexical": 0, "sent_to_llm": 0, "recovered_by_llm": 0,
        "time_lexical_s": 0.0, "time_llm_s": 0.0,
        "roots_es": [], "roots_en": [],
    }

    if not concept:
        return _empty

    if items_override is not None:
        # Use the pre-filtered pool supplied by S3.25 directly.
        items = items_override
        logger.info("Items from S3.25 override: %d (skipping node re-derivation)", len(items))
    else:
        ontology = _load_ontology()
        items = _get_items_for_nodes(ontology, matched_nodes)
        logger.info("Items retrieved from matched nodes: %d", len(items))

    if not items:
        return _empty

    result = filter_hybrid(concept, question, items)

    item_names = [it["item_str"] for it in result["matched"]]

    logger.info(
        "Step 3.5 done: %d/%d kept via '%s' "
        "(lex=%d llm_recovered=%d sent_to_llm=%d | lex=%.4fs llm=%.4fs)",
        result["total_matched"],
        result["total_input"],
        result["path"],
        result.get("matched_by_lexical", result["total_matched"]),
        result.get("recovered_by_llm", 0),
        result.get("sent_to_llm", 0),
        result["time_lexical_s"],
        result["time_llm_s"],
    )
    for name in item_names[:5]:
        logger.info("  → %s", name)
    if len(item_names) > 5:
        logger.info("  ... and %d more", len(item_names) - 5)

    out = {
        "concept": concept,
        "item_names": item_names,
        "path": result["path"],
        "total_input": result["total_input"],
        "total_matched": result["total_matched"],
        "matched_by_lexical": result.get("matched_by_lexical", result["total_matched"]),
        "sent_to_llm": result.get("sent_to_llm", 0),
        "recovered_by_llm": result.get("recovered_by_llm", 0),
        "time_lexical_s": result["time_lexical_s"],
        "time_llm_s": result["time_llm_s"],
        "roots_es": result["roots_es"],
        "roots_en": result["roots_en"],
    }

    # Patch 4 — Surface S3.5 fallback failures.
    # When filter_llm_all's LLM call raises, it silently keeps every item.
    # The signature of that fallback is: Path B, total_input > 0,
    # total_matched == total_input, sent_to_llm > 0.
    if (
        out["path"] == "B"
        and out["total_input"] > 0
        and out["total_matched"] == out["total_input"]
        and out["sent_to_llm"] > 0
    ):
        out["warning"] = (
            "S3.5 Path B kept every item. Likely a clean match, but verify "
            "the LLM actually ran: check logs for \"LLM-all call failed\"."
        )

    return out