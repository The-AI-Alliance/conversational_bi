"""Step 2: validate_retail_domain — 2-phase: LLM extracts, then validates WITH ontology."""

from __future__ import annotations

import logging
import re
from datetime import date

from retail_electronics.config import MODEL_VALIDATE
from retail_electronics.llm.client import chat_json
from retail_electronics.ontology.search3 import search_ontology_items, search_sku
from retail_electronics.tools.display.display import display_s2
from retail_electronics.tools.validate.validator import validate_question

logger = logging.getLogger(__name__)

# ── Phase A: Extract dimensions ──────────────────────────────────────

_EXTRACT_SYSTEM = """You are a dimension extractor for an electronics retailer's analytics system.
Extract structured fields from the user's retail question. Respond in JSON:
{
  "concept": [
    {"main": "<core product noun>", "attribute": "<qualifier, or empty string>"}
  ] or null,
  "metric": "the measurable metric (sales, billing, stock, quantity, revenue, price, units, etc.), or null",
  "date_range": "the time period mentioned as a string, or null",
  "location": "the location mentioned, or null",
  "size": "the specific size or capacity mentioned (e.g. '13', '15', '55', '65', '256GB', '1TB'), or null"
}

For size: extract only the size/capacity value, not the surrounding words ('size'/'inch'/'pulgadas'/'pouces').
  - "13 inch laptops"        → "13"
  - "TVs of 55 inch"         → "55"
  - "pantalla de 65 pulgadas"→ "65"
  - "256GB phones"           → "256GB"

For concept: extract every distinct product or category mentioned as a separate
object in the list. Each object has:
  - "main": the core product noun (what the thing IS)
  - "attribute": an optional qualifier describing which variant/edition/theme

Splitting rules — be STRICT and CONSERVATIVE. When in doubt, put everything
in "main" and leave "attribute" as an empty string "".

SPLIT when the qualifier is clearly separable from the core noun:
  - "wireless headphones"            → {"main": "headphones", "attribute": "wireless"}
  - "gaming laptops"                  → {"main": "laptops",    "attribute": "gaming"}
  - "smart TVs"                       → {"main": "TVs",        "attribute": "smart"}
  - "Bluetooth speakers"              → {"main": "speakers",   "attribute": "Bluetooth"}
  - "noise-cancelling earphones"      → {"main": "earphones",  "attribute": "noise-cancelling"}
  - "4K monitors"                     → {"main": "monitors",   "attribute": "4K"}

DO NOT SPLIT — keep the entire string in "main" with attribute="":
  - Single-word concepts:
      "laptops"      → {"main": "laptops",     "attribute": ""}
      "smartphones"  → {"main": "smartphones", "attribute": ""}
  - Full SKU strings (model designation with capacity/size/color markers):
      'Laptop 13" Ultrabook 16GB/512GB SILVER'
        → {"main": "Laptop 13\\" Ultrabook 16GB/512GB SILVER", "attribute": ""}
  - Near-SKU fragments that look like item names, not generic product types:
      "Smart Speaker Mini WHITE"
        → {"main": "Smart Speaker Mini WHITE", "attribute": ""}
      "Soundbar Premium BLACK"
        → {"main": "Soundbar Premium BLACK", "attribute": ""}
  - Anything ambiguous where you are not confident the qualifier is separable.

Example (multiple concepts):
  "gaming laptops and wireless headphones"
    → [{"main": "laptops",    "attribute": "gaming"},
       {"main": "headphones", "attribute": "wireless"}]

If no concept is mentioned use null.
Only extract what is explicitly mentioned. Use null for unmentioned dimensions."""


def _extract_dimensions(question: str) -> dict:
    """Use gpt-4o-mini to decompose question into concept/metric/date/location."""
    result = chat_json(
        f"Extract dimensions from this question:\n\n{question}",
        model=MODEL_VALIDATE,
        system=_EXTRACT_SYSTEM,
    )
    for key in ("concept", "metric", "date_range", "location", "size"):
        result.setdefault(key, None)
    logger.info("Extracted dimensions: %s", result)
    return result


# ── Phase B: Validate each dimension ─────────────────────────────────

# -- Concept validation --

def _validate_concept(concept) -> dict:
    """Validate one or more concepts.

    Each concept is either a plain string (legacy) or a dict
    {"main": str, "attribute": str}. Validation is performed on the MAIN
    part only (SKU lookup first, then ontology concept lookup). The
    attribute is preserved in the output for downstream use.
    """
    if not concept:
        return {"values": [], "is_valid": True, "reason": "no concept specified"}

    raw_list = [concept] if isinstance(concept, (str, dict)) else list(concept)

    items = []
    for c in raw_list:
        if isinstance(c, dict):
            main = (c.get("main") or "").strip()
            attribute = (c.get("attribute") or "").strip()
        else:
            main = str(c).strip()
            attribute = ""

        if not main:
            # Nothing to look up — treat as invalid
            items.append({
                "value": attribute or "",
                "main": main,
                "attribute": attribute,
                "is_valid": False,
                "reason": "empty main term",
            })
            continue

        display_value = main if not attribute else f"{attribute} {main}"

        sku_result = search_sku(main)
        if sku_result.startswith("SKU FOUND"):
            items.append({
                "value": display_value,
                "main": main,
                "attribute": attribute,
                "is_valid": True,
                "reason": sku_result,
            })
        else:
            onto_result = search_ontology_items(main)
            items.append({
                "value": display_value,
                "main": main,
                "attribute": attribute,
                "is_valid": onto_result.startswith("EXISTS"),
                "reason": onto_result,
            })

    invalid = [it for it in items if not it["is_valid"]]
    is_valid = len(invalid) == 0
    reason = (
        "; ".join(f"'{it['main']}' not found" for it in invalid)
        if invalid
        else "all concepts found"
    )

    return {
        "values": [it["value"] for it in items],
        "is_valid": is_valid,
        "items": items,
        "reason": reason,
    }


# -- Date validation (deterministic Python) --

_MONTH_MAP: dict[str, int] = {
    # English
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    # Spanish
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}

_MIN_DATE = date(2020, 1, 1)


def _validate_date_range(date_range: str | None) -> dict:
    """Validate date range using deterministic Python parsing."""
    if not date_range:
        return {"value": "not specified", "is_valid": True, "reason": "no date specified"}

    today = date.today()
    text = date_range.lower().strip()

    # Try to extract year
    year_match = re.search(r"\b((?:19|20)\d{2})\b", text)
    year = int(year_match.group(1)) if year_match else None

    # Try to extract month
    month = None
    for name, num in _MONTH_MAP.items():
        if name in text:
            month = num
            break

    # Try full date patterns: DD/MM/YYYY, YYYY-MM-DD, etc.
    full_date = None
    full_patterns = [
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", lambda m: (int(m.group(1)), int(m.group(2)), int(m.group(3)))),
        (r"(\d{1,2})/(\d{1,2})/(\d{4})", lambda m: (int(m.group(3)), int(m.group(2)), int(m.group(1)))),
    ]
    for pattern, extractor in full_patterns:
        m = re.search(pattern, text)
        if m:
            try:
                y, mo, d = extractor(m)
                full_date = date(y, mo, d)
            except ValueError:
                pass
            break

    # Determine the reference date to validate
    if full_date:
        ref_date = full_date
    elif year and month:
        ref_date = date(year, month, 1)
    elif year:
        ref_date = date(year, 1, 1)
    else:
        # Could not parse any date — assume it's a relative reference, pass through
        return {
            "value": date_range,
            "is_valid": True,
            "reason": "relative or unparseable date reference, accepted permissively",
        }

    # Validate range
    if ref_date < _MIN_DATE:
        return {
            "value": date_range,
            "is_valid": False,
            "reason": f"date {ref_date.isoformat()} is before {_MIN_DATE.year} (no data available)",
        }

    if ref_date > today:
        return {
            "value": date_range,
            "is_valid": False,
            "reason": f"date {ref_date.isoformat()} is in the future (today is {today.isoformat()})",
        }

    return {
        "value": date_range,
        "is_valid": True,
        "reason": f"date is within valid range ({_MIN_DATE.year} to {today.isoformat()})",
    }


# -- Location validation (LLM) --

_LOCATION_SYSTEM = """You are a location validator for an electronics retailer's analytics system.
Determine if the location is valid for a retail query.

Rules:
- Earth-based locations or no location → VALID
- Moon, Mars, fictional places, or clearly non-existent locations → INVALID

Respond in JSON:
{
  "is_valid": true/false,
  "reason": "brief explanation"
}"""


def _validate_location(location: str | None) -> dict:
    """Validate location using LLM simple check."""
    if not location:
        return {"value": "not specified", "is_valid": True, "reason": "no location specified"}

    result = chat_json(
        f'Is this a valid real-world location for a retail query? Location: "{location}"',
        model=MODEL_VALIDATE,
        system=_LOCATION_SYSTEM,
    )

    return {
        "value": location,
        "is_valid": result.get("is_valid", False),
        "reason": result.get("reason", "unknown"),
    }


# -- Metric validation (validator.py system) --

def _validate_metric(question: str) -> dict:
    """Validate the metric/analytical intent using the validator system.

    Runs the full question through Step A (LLM decomposition) + Step B
    (deterministic ontology checks). Returns the standard
    {"value", "is_valid", "reason"} shape plus the full step_a / step_b
    payloads so callers can inspect why a verdict was reached.
    """
    result = validate_question(question)
    step_a = result["step_a"]
    step_b = result["step_b"]

    # Use the metric(s) identified by the LLM as the display value
    metrics = step_a.get("metrics", [])
    value = metrics[0] if len(metrics) == 1 else (metrics if metrics else None)

    verdict = step_b["verdict"]

    base = {
        "value": value,
        "metrics": metrics,
        "dimensions": step_a.get("dimensions", []),
        "operations": step_a.get("operations", []),
        "filters": step_a.get("filters", []),
        "operation_details": step_a.get("operation_details", {}),
        "ambiguities": step_a.get("ambiguities", []),
        "unmatched_concepts": step_a.get("unmatched_concepts", []),
        "verdict": verdict,
        "step_a": step_a,
        "step_b": step_b,
    }

    if verdict == "valid":
        return {**base, "is_valid": True, "reason": "valid analytical intent"}

    if verdict == "out_of_scope":
        return {
            **base,
            "is_valid": False,
            "reason": step_b.get("message", step_b.get("reason", "out of scope")),
            "failed_check": "out_of_scope",
            "matched_boundary": step_b.get("matched_boundary"),
            "unmatched_concept": step_b.get("unmatched_concept"),
        }

    # invalid
    return {
        **base,
        "is_valid": False,
        "reason": step_b.get("reason", "invalid"),
        "failed_check": step_b.get("failed_check"),
        "suggestion": step_b.get("suggestion"),
    }


# ── Orchestrator ─────────────────────────────────────────────────────

def validate_retail_domain(question: str) -> dict:
    """Validate that question is answerable within the electronics retail domain.

    Phase A: LLM extracts dimensions (concept, metric, date_range, location).
    Phase B: Validates each — concept via ontology+LLM, date via Python,
             location via LLM, metric via Python.

    Args:
        question: The user's question (already classified as electronics_retail).

    Returns:
        dict with is_valid, concept, date_range, location, suggestion.
    """
    logger.info("=" * 60)
    logger.info("STEP 2: VALIDATE RETAIL DOMAIN")
    logger.info("Question: %s", question)

    # Phase A: Extract
    dims = _extract_dimensions(question)

    # Phase B: Validate each dimension
    concept_result = _validate_concept(dims.get("concept"))
    date_result = _validate_date_range(dims.get("date_range"))
    location_result = _validate_location(dims.get("location"))
    metric_result = _validate_metric(question)
    # Size: extracted but not validated — any non-null string is accepted as-is
    size_value = dims.get("size")

    is_valid = all([
        concept_result["is_valid"],
        date_result["is_valid"],
        location_result["is_valid"],
        metric_result["is_valid"],
    ])

    # Build suggestion if invalid
    suggestion = None
    if not is_valid:
        reasons = []
        if not concept_result["is_valid"]:
            reasons.append(f"concept: {concept_result['reason']}")
        if not date_result["is_valid"]:
            reasons.append(f"date: {date_result['reason']}")
        if not location_result["is_valid"]:
            reasons.append(f"location: {location_result['reason']}")
        if not metric_result["is_valid"]:
            reasons.append(f"metric: {metric_result['reason']}")
        suggestion = "Invalid because: " + "; ".join(reasons)

    result = {
        "is_valid": is_valid,
        "concept": concept_result,
        "date_range": date_result,
        "location": location_result,
        "metric": metric_result,
        "size": size_value,
        "suggestion": suggestion,
    }

    # Log results
    logger.info("Valid: %s", is_valid)
    for dim in ("concept", "date_range", "location", "metric"):
        d = result[dim]
        status = "+" if d.get("is_valid") else "-"
        value = d.get("values") or d.get("value")
        logger.info("  %s %s: %s — %s", status, dim, value, d.get("reason"))
    logger.info("  • size: %s", size_value)

    if suggestion:
        logger.info("Suggestion: %s", suggestion)

    result['display'] = display_s2(result)
    return result
