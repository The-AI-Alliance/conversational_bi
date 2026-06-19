"""Ontology existence check using ontology_synonyms.json.

Given a concept (e.g. "wireless headphones", "laptop", "smart TV") returns
whether that concept exists in the product ontology.

Also provides search_sku() for direct item_name lookups against the
master_articles parquet (handles copy-pasted SKU names or partial fragments).
"""

from __future__ import annotations

import json
import logging
from difflib import SequenceMatcher
from pathlib import Path

import duckdb

from retail_electronics.config import ONTOLOGY_JSON_PATH, PARQUET_DIR

logger = logging.getLogger(__name__)

# Resolved alongside the existing ontology JSON
_SYNONYMS_PATH: Path = ONTOLOGY_JSON_PATH.parent / "ontology_synonyms.json"
_MASTER_ARTICLES: Path = PARQUET_DIR / "master_articles_oitm.parquet"

# Higher threshold than the ranked-search one — a binary yes/no answer
# must be conservative to avoid false positives.
# 0.87 was chosen because all known false-positive fuzzy matches (e.g.
# "training shirt" ≈ "training shoes", "home shorts" ≈ "home shirt") score
# in the 0.82–0.86 range, while every genuine match is already caught by
# exact or substring (_covers) checks before fuzzy is reached.
_FUZZY_THRESHOLD = 0.87

# Module-level cache so the file is only read once per process
_synonyms_data: dict | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _load() -> dict:
    global _synonyms_data
    if _synonyms_data is None:
        if not _SYNONYMS_PATH.exists():
            raise FileNotFoundError(
                f"ontology_synonyms.json not found at {_SYNONYMS_PATH}"
            )
        with open(_SYNONYMS_PATH, encoding="utf-8") as fh:
            _synonyms_data = json.load(fh)
    return _synonyms_data


def _flatten(node: dict, path: str = "") -> list[tuple[str, str, list[str]]]:
    """DFS-flatten the synonyms tree into (path, name, synonyms) tuples.

    Skips the root node (empty name / no useful synonyms).
    """
    results: list[tuple[str, str, list[str]]] = []
    name: str = node.get("name", "")
    synonyms: list[str] = node.get("synonyms", [])

    current_path = f"{path}/{name}".strip("/") if name else path

    if name:
        results.append((current_path, name, synonyms))

    for child_node in node.get("children", {}).values():
        results.extend(_flatten(child_node, current_path))

    return results


def _ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _covers(needle: str, haystack: str) -> bool:
    """True if needle is a substring of haystack AND covers ≥ 60 % of haystack.

    This prevents short generic synonyms (e.g. "shirt", "home", "wear") from
    triggering a match on longer multi-word concepts (e.g. "training shirt",
    "home shorts", "swimwear").
    """
    if needle not in haystack:
        return False
    return len(needle) >= 0.60 * len(haystack)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_sku(concept: str) -> str:
    """Check whether a concept matches a real item_name in master_articles.

    Designed for copy-pasted SKU names or partial fragments, e.g.:
      - 'Laptop 13" Ultrabook 16GB/512GB SILVER'  (full)
      - 'Laptop 13" Ultrabook 16GB'                (partial)
      - 'Laptop Ultrabook'                          (minimal)

    Every token in the concept must appear in item_name (ILIKE AND).
    If any row matches → SKU FOUND.

    Args:
        concept: Any fragment of an item name.

    Returns:
        ``"SKU FOUND: <base_name>"`` with the deduplicated product name,
        or ``"NOT FOUND"`` when no item matches.
    """
    concept = concept.strip()
    if not concept:
        return "NOT FOUND"

    if not _MASTER_ARTICLES.exists():
        logger.warning("master_articles parquet not found at %s", _MASTER_ARTICLES)
        return "NOT FOUND"

    # Tokenize and sanitize (escape single quotes)
    tokens = [t.replace("'", "''") for t in concept.split() if t]
    if not tokens:
        return "NOT FOUND"

    # Every token must appear in item_name (case-insensitive)
    where = " AND ".join(f"item_name ILIKE '%{tok}%'" for tok in tokens)

    sql = f"""
        SELECT item_name
        FROM '{_MASTER_ARTICLES}'
        WHERE {where}
          AND item_name NOT LIKE '%(NO USAR)%'
        LIMIT 1
    """

    try:
        rows = duckdb.sql(sql).fetchall()
    except Exception as e:
        logger.warning("search_sku DuckDB error: %s", e)
        return "NOT FOUND"

    if not rows:
        return "NOT FOUND"

    result = f"SKU FOUND: {rows[0][0]}"
    logger.debug("search_sku(%r) → %s", concept, result)
    return result


def search_ontology_items(concept: str) -> str:
    """Check whether a concept exists in the product ontology.

    Scans ``ontology_synonyms.json`` in three separate passes so that
    exact synonym matches always beat fuzzy matches, regardless of node
    order in the file:

      Pass 1 — Exact: concept == node name  OR  concept == any synonym
      Pass 2 — Covers: a text covers ≥ 60 % of the other (prevents short
               synonyms like "shirt" or "home" from matching longer concepts)
      Pass 3 — Fuzzy: SequenceMatcher ratio ≥ _FUZZY_THRESHOLD (0.87)

    Args:
        concept: Free-text concept to look up, e.g. "wireless headphones",
                 "ultrabook", "noise-cancelling earbuds".

    Returns:
        ``"EXISTS: <path>"`` with the matching ontology path when found,
        or ``"NOT FOUND"`` when no node matches.

    Examples:
        >>> search_ontology_items("wireless headphones")
        "EXISTS: .../Over-Ear Wireless Headphones (matched synonym: 'wireless headphones')"

        >>> search_ontology_items("laptop")
        'EXISTS: .../Laptops'

        >>> search_ontology_items("typewriter")
        'NOT FOUND'
    """
    concept = concept.strip()
    if not concept:
        return "NOT FOUND"

    data = _load()
    nodes = _flatten(data)
    c = concept.lower()

    # ------------------------------------------------------------------
    # Pass 1: exact matches (wins regardless of JSON traversal order)
    # ------------------------------------------------------------------
    for node_path, name, synonyms in nodes:
        n = name.lower()
        if c == n:
            result = f"EXISTS: {node_path}"
            logger.debug("search_ontology_items(%r) → %s [exact]", concept, result)
            return result
        for syn in synonyms:
            if c == syn.lower():
                result = f"EXISTS: {node_path} (matched synonym: '{syn}')"
                logger.debug("search_ontology_items(%r) → %s [exact syn]", concept, result)
                return result

    # ------------------------------------------------------------------
    # Pass 2: covers-based substring matches
    # ------------------------------------------------------------------
    for node_path, name, synonyms in nodes:
        n = name.lower()
        if _covers(n, c) or _covers(c, n):
            result = f"EXISTS: {node_path}"
            logger.debug("search_ontology_items(%r) → %s [covers]", concept, result)
            return result
        for syn in synonyms:
            s = syn.lower()
            if _covers(s, c) or _covers(c, s):
                result = f"EXISTS: {node_path} (matched synonym: '{syn}')"
                logger.debug("search_ontology_items(%r) → %s [covers syn]", concept, result)
                return result

    # ------------------------------------------------------------------
    # Pass 3: fuzzy matches (last resort)
    # ------------------------------------------------------------------
    for node_path, name, synonyms in nodes:
        n = name.lower()
        score_name = _ratio(c, n)
        if score_name >= _FUZZY_THRESHOLD:
            result = f"EXISTS: {node_path} (fuzzy match: '{name}', score {score_name:.2f})"
            logger.debug("search_ontology_items(%r) → %s [fuzzy]", concept, result)
            return result
        for syn in synonyms:
            score = _ratio(c, syn.lower())
            if score >= _FUZZY_THRESHOLD:
                result = f"EXISTS: {node_path} (fuzzy synonym: '{syn}', score {score:.2f})"
                logger.debug("search_ontology_items(%r) → %s [fuzzy syn]", concept, result)
                return result

    logger.debug("search_ontology_items(%r) → NOT FOUND", concept)
    return "NOT FOUND"
