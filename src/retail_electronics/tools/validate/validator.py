"""
Conversational BI — Question Validator
=======================================

Two-step pipeline:
  Step A — LLM-based decomposition of a natural language question into a
           structured intent.
  Step B — Deterministic validation of that intent against the ontology.

Usage:
    from retail_electronics.tools.validate.validator import validate_question

    result = validate_question("What was the total billing for Summer 2025?")
    print(result["step_a"])    # structured intent from LLM
    print(result["step_b"])    # verdict: valid / invalid / out_of_scope
"""

import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from retail_electronics.config import OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_VALIDATE


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ONTOLOGY_PATH = Path(__file__).resolve().parents[4] / "data" / "ontology" / "ontology_metrics.json"
OPENAI_MODEL = MODEL_VALIDATE

_client: OpenAI | None = None
_ontology: dict[str, Any] | None = None


def _get_client() -> OpenAI:
    """Lazy-load the OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _client


def _get_ontology() -> dict[str, Any]:
    """Lazy-load the ontology JSON once."""
    global _ontology
    if _ontology is None:
        with open(ONTOLOGY_PATH) as f:
            _ontology = json.load(f)
    return _ontology


# ---------------------------------------------------------------------------
# Step A — LLM Decomposition
# ---------------------------------------------------------------------------

def _build_step_a_prompt(ontology: dict[str, Any]) -> str:
    metrics_summary = {
        name: {
            "description": m["description"],
            "measure_type": m["measure_type"],
            "temporal_nature": m["temporal_nature"],
            "aliases": m["aliases"],
        }
        for name, m in ontology["metrics"].items()
    }

    dimensions_summary = {
        name: {
            "description": d["description"],
            "type": d["type"],
            "hierarchy": d.get("hierarchy"),
            "known_values": d.get("known_values"),
            "aliases": d["aliases"],
        }
        for name, d in ontology["dimensions"].items()
    }

    operations_summary = {
        name: {
            "description": op["description"],
            "trigger_phrases": op["trigger_phrases"],
            **({"allowed_ratios": list(op["allowed_ratios"].keys())}
               if "allowed_ratios" in op else {}),
        }
        for name, op in ontology["operations"].items()
    }

    return f"""You are a disciplined intent extractor for a Conversational BI system.

Your ONLY job is to translate a natural language question into a structured
JSON intent. You do NOT judge whether the question can be answered — another
system does that. You only report what you see.

# Available METRICS
{json.dumps(metrics_summary, indent=2, ensure_ascii=False)}

# Available DIMENSIONS
{json.dumps(dimensions_summary, indent=2, ensure_ascii=False)}

# Available OPERATIONS
{json.dumps(operations_summary, indent=2, ensure_ascii=False)}

# Output schema
Return ONLY a JSON object with this exact structure:
{{
  "metrics": [<canonical metric names from the catalog>],
  "dimensions": [<canonical dimension names referenced for grouping or filtering>],
  "filters": [
    {{"dimension": "<canonical name>", "level": "<hierarchy level if applicable>",
      "value": "<specific value from the question>"}}
  ],
  "operations": [<canonical operation names>],
  "operation_details": {{
    "<operation_name>": {{ ... any specifics such as period comparisons, ratio type, etc. }}
  }},
  "ambiguities": [
    {{"element": "<metric|dimension|operation|level>", "reason": "<short reason>"}}
  ],
  "unmatched_concepts": [
    {{"term": "<exact phrase from the question>",
      "suspected_type": "<metric|dimension|operation>",
      "reason": "<short reason>"}}
  ]
}}

# Critical rules
1. NEVER invent metrics, dimensions, or operations that are not in the catalogs above.
2. `unmatched_concepts` is reserved EXCLUSIVELY for terms that look like a
   metric but have no match in the metric catalog (suspected_type="metric").
   Do NOT add dimension-level or operation-level terms to `unmatched_concepts`
   — those are handled elsewhere. Do NOT force a match to the closest
   available metric.
3. Product terms (e.g. "laptops", "smartphones", "headphones", "speakers",
   "gaming consoles", full SKU strings like
   'Laptop 13" Ultrabook 16GB/512GB SILVER') are validated
   by a separate product-ontology system — they are NOT part of this
   catalog. When a specific product term appears in the question, you MUST:
     - include `product_reference` in `dimensions`
     - emit a filter
       {{"dimension": "product_reference",
        "level": "item" if the term looks like a full SKU, else "concept",
        "value": "<the product term as written in the question>"}}
     - do NOT add that term to `unmatched_concepts`.
4. If the user asks "how much" about money, prefer `billing`. If they ask
   "how many" about units, prefer `items_sold`.
5. If no explicit operation is mentioned, default to `total`.
6. For derived ratios (like "sell-through rate", "average price"), set
   operations=["derived_ratio"] and put the specific ratio name in
   operation_details.derived_ratio.ratio_name. You MUST also populate
   `metrics` with the ratio's NUMERATOR metric only (the "answer" metric).
   The full formula is already captured by ratio_name; listing the
   numerator alone avoids multi-metric-pair conflicts. Mapping:
     - average_selling_price            → metrics=["billing"]
     - sell_through_rate_from_stock     → metrics=["items_sold"]
     - sell_through_rate_from_received  → metrics=["items_sold"]
     - internal_consumption_share       → metrics=["internal_consumption"]
7. For comparisons across two specific time periods, use `period_over_period`
   and specify the two periods in operation_details.
8. For questions asking about "reasons" without mentioning notes/comments/
   commentary, prefer breakdown by `internal_reason` (a structured dimension),
   not `text_search`.
9. Every field in the output schema must be present, even as an empty array.
10. Return ONLY the JSON object, no prose, no code fences.
"""


def step_a_decompose(question: str) -> dict[str, Any]:
    """Step A: call the LLM to decompose a question into a structured intent."""
    ontology = _get_ontology()
    system_prompt = _build_step_a_prompt(ontology)

    client = _get_client()
    response = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )

    raw = response.choices[0].message.content
    intent = json.loads(raw)

    intent.setdefault("metrics", [])
    intent.setdefault("dimensions", [])
    intent.setdefault("filters", [])
    intent.setdefault("operations", [])
    intent.setdefault("operation_details", {})
    intent.setdefault("ambiguities", [])
    intent.setdefault("unmatched_concepts", [])

    return intent


# ---------------------------------------------------------------------------
# Step B — Deterministic Validation
# ---------------------------------------------------------------------------

def _match_boundary(unmatched_term: str, ontology: dict[str, Any]) -> dict | None:
    term_lower = unmatched_term.lower()
    for boundary in ontology["boundaries"]["out_of_scope_concepts"]:
        for keyword in boundary["keywords"]:
            if keyword.lower() in term_lower or term_lower in keyword.lower():
                return boundary
    return None


def _out_of_scope(unmatched: list[dict], ontology: dict[str, Any]) -> dict:
    matched_boundary = None
    matched_term = None
    for u in unmatched:
        if u.get("suspected_type") == "metric":
            matched_boundary = _match_boundary(u["term"], ontology)
            matched_term = u["term"]
            if matched_boundary:
                break

    if matched_boundary:
        message = (
            f"This question is about {matched_boundary['concept'].lower()}, "
            f"which is outside what I can compute. {matched_boundary['reason']} "
            f"I can answer questions about billing, items sold, items received, "
            f"internal consumption, and stock."
        )
        return {
            "verdict": "out_of_scope",
            "unmatched_concept": matched_term,
            "matched_boundary": matched_boundary["concept"],
            "reason": matched_boundary["reason"],
            "message": message,
        }

    generic_term = unmatched[0]["term"] if unmatched else "unknown"
    return {
        "verdict": "out_of_scope",
        "unmatched_concept": generic_term,
        "matched_boundary": None,
        "reason": "The question does not map to any known metric.",
        "message": (
            f"I could not identify a known metric in your question. "
            f"I can answer questions about billing, items sold, items received, "
            f"internal consumption, and stock."
        ),
    }


def _invalid(failed_check: str, reason: str, suggestion: str,
             suggested_intent: dict | None = None) -> dict:
    return {
        "verdict": "invalid",
        "failed_check": failed_check,
        "reason": reason,
        "suggestion": suggestion,
        "suggested_intent": suggested_intent,
    }


def _valid(intent: dict) -> dict:
    return {
        "verdict": "valid",
        "enriched_intent": intent,
    }


def step_b_validate(intent: dict[str, Any]) -> dict[str, Any]:
    """Step B: deterministic validation of the structured intent against the ontology."""
    ontology = _get_ontology()
    metrics = intent.get("metrics", [])
    dimensions = intent.get("dimensions", [])
    operations = intent.get("operations", [])
    unmatched = intent.get("unmatched_concepts", [])
    op_details = intent.get("operation_details", {})

    # Check 0 — Out-of-scope early exit
    has_metric_unmatched = any(
        u.get("suspected_type") == "metric" for u in unmatched
    )
    if not metrics and has_metric_unmatched:
        return _out_of_scope(unmatched, ontology)

    if not metrics and not has_metric_unmatched:
        return _invalid(
            failed_check="no_metric_identified",
            reason="The question does not reference any known metric clearly.",
            suggestion=(
                "Please rephrase using one of: billing, items sold, items received, "
                "internal consumption, or stock."
            ),
        )

    # Check 1 — Metric existence
    for m in metrics:
        if m not in ontology["metrics"]:
            return _invalid(
                failed_check="metric_existence",
                reason=f"Metric '{m}' is not defined in the ontology.",
                suggestion="Please rephrase using a known metric.",
            )

    # Check 2 — Multi-metric validity
    if len(metrics) > 1:
        mm = ontology["multi_metric_support"]
        if len(metrics) > mm["max_metrics_per_intent"]:
            return _invalid(
                failed_check="multi_metric_limit",
                reason=f"Questions can reference at most {mm['max_metrics_per_intent']} metrics.",
                suggestion="Please ask about one metric at a time.",
            )
        pair = sorted(metrics)
        allowed = [sorted(p) for p in mm["allowed_metric_pairs"]]
        if pair not in allowed:
            return _invalid(
                failed_check="multi_metric_pair",
                reason=f"The combination {metrics} is not supported as a joint question.",
                suggestion=(
                    "Supported pairs are: billing & items_sold, "
                    "items_sold & items_received, items_sold & stock, "
                    "items_received & stock. Please ask about them separately."
                ),
            )

    # Check 3 — Dimension compatibility
    compat = ontology["metric_dimension_compatibility"]
    for dim in dimensions:
        if dim not in ontology["dimensions"]:
            return _invalid(
                failed_check="dimension_existence",
                reason=f"Dimension '{dim}' is not defined in the ontology.",
                suggestion="Please rephrase using a known dimension.",
            )
        for m in metrics:
            if dim not in compat[m]:
                compatible = compat[m]
                return _invalid(
                    failed_check="dimension_compatibility",
                    reason=f"Dimension '{dim}' is not compatible with metric '{m}'.",
                    suggestion=(
                        f"'{m}' can be analyzed by: {', '.join(compatible)}. "
                        f"Would you like to rephrase using one of these?"
                    ),
                )

    # Check 4 — Temporal nature vs operation
    for op in operations:
        if op not in ontology["operations"]:
            return _invalid(
                failed_check="operation_existence",
                reason=f"Operation '{op}' is not defined in the ontology.",
                suggestion="Please rephrase your question.",
            )
        op_def = ontology["operations"][op]
        valid_natures = op_def.get("valid_for_temporal_nature", ["flow", "snapshot"])
        for m in metrics:
            metric_nature = ontology["metrics"][m]["temporal_nature"]
            if metric_nature not in valid_natures:
                if metric_nature == "snapshot" and op == "time_averaged":
                    return _invalid(
                        failed_check="temporal_nature_mismatch",
                        reason=(
                            f"'{m}' is a point-in-time balance, not a flow. "
                            f"It cannot be averaged over a period in the usual sense."
                        ),
                        suggestion=(
                            f"I can show you the {m} level at the end of each "
                            f"period, or the trend of {m} over time. Which would "
                            f"you prefer?"
                        ),
                    )
                return _invalid(
                    failed_check="temporal_nature_mismatch",
                    reason=f"Operation '{op}' is not valid for {metric_nature} metric '{m}'.",
                    suggestion=(
                        f"'{m}' is a {metric_nature} metric. Try asking for "
                        f"its value at a point in time or its trend over time."
                    ),
                )

    # Check 4.5 — Special case: "total" over a period for snapshot metric
    for m in metrics:
        if ontology["metrics"][m]["temporal_nature"] == "snapshot":
            if "total" in operations:
                for f in intent.get("filters", []):
                    if f.get("dimension") == "time_calendar":
                        level = f.get("level", "")
                        if level in ("year", "quarter", "month", "week"):
                            intent["operation_details"].setdefault("total", {})
                            intent["operation_details"]["total"]["snapshot_interpretation"] = (
                                f"balance at end of {f.get('value')}"
                            )

    # Check 5 — Derived ratio whitelist
    if "derived_ratio" in operations:
        ratio_details = op_details.get("derived_ratio", {})
        ratio_name = ratio_details.get("ratio_name")
        allowed = ontology["operations"]["derived_ratio"]["allowed_ratios"]
        if ratio_name and ratio_name not in allowed:
            available = list(allowed.keys())
            return _invalid(
                failed_check="derived_ratio_not_whitelisted",
                reason=f"The ratio '{ratio_name}' is not a supported business ratio.",
                suggestion=(
                    f"Supported ratios are: {', '.join(available)}. "
                    f"Would any of these fit your question?"
                ),
            )

    # Check 6 — Forecast eligibility
    if "forecast" in operations:
        for m in metrics:
            if not ontology["metrics"][m].get("supports_forecast", False):
                return _invalid(
                    failed_check="forecast_not_supported",
                    reason=f"Metric '{m}' does not support forecasting.",
                    suggestion=(
                        "Forecasting is supported for billing, items sold, "
                        "and stock only."
                    ),
                )

    # Check 7 — Text search compatibility
    if "text_search" in operations:
        for m in metrics:
            if m != "internal_consumption":
                return _invalid(
                    failed_check="text_search_not_compatible",
                    reason=(
                        f"Commentary search is only available for internal "
                        f"consumption, not for '{m}'."
                    ),
                    suggestion=(
                        "Text search on commentary only applies to internal "
                        "consumption."
                    ),
                )

    # Check 8 — Composition depth
    max_ops = ontology["composition_rules"]["max_operations_per_query"]
    if len(operations) > max_ops:
        return _invalid(
            failed_check="composition_depth",
            reason=(
                f"This question involves {len(operations)} analytical steps, "
                f"which exceeds the limit of {max_ops}."
            ),
            suggestion=(
                "Could you break this into two simpler questions? For example, "
                "first ask about the trend, then about the ranking."
            ),
        )

    # Check 9 — Forbidden combinations
    for forbidden in ontology["composition_rules"]["forbidden_combinations"]:
        fops = forbidden["operations"]
        if len(fops) == 2 and fops[0] == fops[1]:
            if operations.count(fops[0]) >= 2:
                return _invalid(
                    failed_check="forbidden_combination",
                    reason=forbidden["reason"],
                    suggestion="Please simplify your question.",
                )
        else:
            if all(f in operations for f in fops):
                return _invalid(
                    failed_check="forbidden_combination",
                    reason=forbidden["reason"],
                    suggestion="Please rephrase to avoid combining these operations.",
                )

    # Check 10 — Operation chaining
    for op in operations:
        op_def = ontology["operations"][op]
        accepts = op_def.get("accepts_input_from", [])
        if not accepts:
            continue
        if len(operations) > 1:
            other_ops = [o for o in operations if o != op]
            if not any(o in accepts for o in other_ops):
                if op in ("breakdown", "ranking"):
                    continue
                if op == "pattern_detection":
                    return _invalid(
                        failed_check="operation_chaining",
                        reason=(
                            "Pattern detection needs a trend or a growth "
                            "comparison to operate on."
                        ),
                        suggestion=(
                            "Try asking: 'What patterns can you observe in "
                            "billing month by month in 2025?'"
                        ),
                    )

    return _valid(intent)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_question(question: str) -> dict[str, Any]:
    """Main entry point: Step A (LLM decomposition) + Step B (deterministic validation).

    Returns:
        {
            "question": <original question>,
            "step_a": <structured intent from LLM>,
            "step_b": <verdict: valid | invalid | out_of_scope>
        }
    """
    step_a_result = step_a_decompose(question)
    step_b_result = step_b_validate(step_a_result)

    return {
        "question": question,
        "step_a": step_a_result,
        "step_b": step_b_result,
    }
