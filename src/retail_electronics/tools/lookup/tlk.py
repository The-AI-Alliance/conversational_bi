"""Step 4: tlk_lookup_v3 — deterministic IN-based SQL generation (final version).

Improvements over tlk_lookup.py (v1):
- item_names and metric_info are explicit first-class parameters instead of
  being buried inside ontology_context.
- Replaces ILIKE '%<ITEM_NAME>%' with an exact item_name IN (...) clause
  built from the deterministic SKU list produced by Step 3.5.
- Injects validated metric and operation from Step 2 into every LLM prompt
  so the model never has to re-infer analytical intent from raw question text.
- Handles multi-year date ranges via <YYYY_START> / <YYYY_END> placeholders.
- MEDIUM and LOW prompts include an explicit table catalogue to prevent the
  LLM from hallucinating non-existent table names.
- Fully standalone — no imports from tlk_lookup.py.

Typical call:

    s4 = tlk_lookup_v3(
        question    = question,
        item_names  = s35["item_names"],       # list[str] from Step 3.5
        date_range  = s2["date_range"],        # dict from Step 2
        metric_info = {
            "metrics":           s2["metric"]["metrics"],
            "operations":        s2["metric"]["operations"],
            "operation_details": s2["metric"]["operation_details"],
            "filters":           s2["metric"]["filters"],
        },
        ontology_context = s3b,                # optional, for schema hints
    )
"""

from __future__ import annotations

import json
import logging
import re

from retail_electronics.config import (
    DDL_PATH,
    MODEL_TLK,
    ONTOLOGY_JSON_PATH,
    TLK_LIBRARY_PATH,
)
from retail_electronics.llm.client import chat, chat_json
from retail_electronics.tools.lookup.date_guards import _is_complex_date

logger = logging.getLogger(__name__)

# Maximum number of items in the IN clause (DuckDB handles large lists fine,
# but we cap for SQL readability and prompt size).
_IN_LIST_MAX = 100000

# Explicit table catalogue injected into MEDIUM/LOW prompts so the LLM never
# invents table names.
_TABLE_CATALOGUE = """\
Available tables in the retail2 schema (use ONLY these):
  retail2.inventory_stock_inv1      — sales invoice LINES  (quantity, line_total, item_code, doc_date, ocr_code)
  retail2.sales_credit_notes_rin1   — credit note LINES    (quantity, line_total, item_code, doc_date, ocr_code)
  retail2.master_articles_oitm      — product master       (item_code, item_name)
  retail2.master_stock_oitw         — stock levels         (item_code, on_hand, warehouse_code)
  retail2.master_inventory_log_oinm — inventory movements

NEVER use any other table name. In particular, retail2.sales_invoices_inv1 does NOT exist.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_library() -> list[dict]:
    try:
        with open(TLK_LIBRARY_PATH) as f:
            return json.load(f)["library"]
    except Exception as e:
        logger.warning("Failed to load TLK library: %s", e)
        return []


def _load_ddl() -> str:
    try:
        return DDL_PATH.read_text()
    except Exception:
        return ""


def _get_ontology_sample(ontology_context: dict | None) -> str:
    """Return a short sample of matching items for LLM prompt context."""
    if not ontology_context:
        return ""

    item_matches = ontology_context.get("item_matches", [])
    if item_matches:
        lines = [
            f"- {m['item_name']} (code: {m['item_code']})"
            for m in item_matches[:5]
        ]
        return "Exact item matches from database:\n" + "\n".join(lines)

    if not ontology_context.get("matched_nodes"):
        return ""

    try:
        with open(ONTOLOGY_JSON_PATH) as f:
            full_ont = json.load(f)

        samples = []
        for node in ontology_context["matched_nodes"][:3]:
            path_parts = node.get("path", "").split("/")
            current = full_ont.get("children", {})
            for part in path_parts:
                if part in current:
                    current = current[part]
                    if "children" in current:
                        current = current["children"]
            if isinstance(current, dict) and "sample_items" in current:
                samples.extend(current["sample_items"][:3])

        if samples:
            return "Sample matching items:\n" + "\n".join(f"- {s}" for s in samples)
    except Exception as e:
        logger.warning("Failed to get ontology samples: %s", e)

    return ""


def _normalize_question(
    question: str,
    ontology_context: dict | None,
    date_range: dict | None,
) -> str:
    """Replace concrete values with placeholder tokens for template matching."""
    normalized = question

    if ontology_context:
        item_matches = ontology_context.get("item_matches", [])
        if item_matches:
            concept = ontology_context.get("concept", "")
            if concept and concept.lower() in normalized.lower():
                normalized = re.sub(re.escape(concept), "<ITEM_NAME>", normalized, flags=re.IGNORECASE)
            else:
                item_name = item_matches[0]["item_name"]
                if item_name in normalized:
                    normalized = normalized.replace(item_name, "<ITEM_NAME>")
        elif ontology_context.get("matched_nodes"):
            concept = ontology_context.get("concept", "")
            if concept and concept.lower() in normalized.lower():
                normalized = re.sub(re.escape(concept), "<ITEM_NAME>", normalized, flags=re.IGNORECASE)
            else:
                first = ontology_context["matched_nodes"][0]
                for field in ("product_type", "product_category", "subfamily", "family"):
                    name = first.get(field)
                    if name and name.lower() in normalized.lower():
                        normalized = re.sub(re.escape(name), "<ITEM_NAME>", normalized, flags=re.IGNORECASE)
                        break

    month_names = [
        "january", "february", "march", "april", "may", "june",
        "july", "august", "september", "october", "november", "december",
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ]
    for name in month_names:
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(normalized):
            normalized = pattern.sub("<MM>", normalized)
            break

    # First year → <YYYY_START>, second year → <YYYY_END>, single year → <YYYY>
    years_found = re.findall(r"\b20\d{2}\b", normalized)
    if len(years_found) >= 2:
        normalized = re.sub(r"\b20\d{2}\b", "<YYYY_START>", normalized, count=1)
        normalized = re.sub(r"\b20\d{2}\b", "<YYYY_END>",   normalized, count=1)
    else:
        normalized = re.sub(r"\b20\d{2}\b", "<YYYY>", normalized)

    normalized = re.sub(r"\d{2}/\d{2}\s*-\s*(?=<ITEM_NAME>)", "", normalized)
    return normalized


def _build_in_clause(item_names: list[str], alias: str = "o") -> str:
    """Build a SQL IN clause from exact item_name strings."""
    if not item_names:
        return ""

    capped = item_names[:_IN_LIST_MAX]
    if len(item_names) > _IN_LIST_MAX:
        logger.warning(
            "_build_in_clause: capped item list from %d to %d items",
            len(item_names), _IN_LIST_MAX,
        )

    quoted = ", ".join(f"'{n.replace(chr(39), chr(39) * 2)}'" for n in capped)
    return f"{alias}.item_name IN ({quoted})"


def _fill_placeholders_v3(
    sql_template: str,
    item_names: list[str] | None,
    date_range: dict | None,
) -> str:
    """Replace <PLACEHOLDER> tokens in a TLK SQL template.

    Item filter:
      item_names provided → replace IN ('<ITEM_NAME>') token with full quoted list.
      item_names empty    → strip the IN clause and its preceding AND entirely.

    Date filter:
      Handles single year (<YYYY>), multi-year (<YYYY_START>/<YYYY_END>),
      and month+year (<MM> / <YYYY>).
    """
    sql = sql_template

    # ── Item filter ───────────────────────────────────────────────────────
    # ── Item filter ───────────────────────────────────────────────────────
    if item_names:
        # All templates now use IN ('<ITEM_NAME>') — plain token replace
        quoted = ", ".join(
            f"'{n.replace(chr(39), chr(39) * 2)}'" for n in item_names[:_IN_LIST_MAX]
        )
        sql = sql.replace("'<ITEM_NAME>'", quoted)
    else:
        # No SKUs — drop the entire IN filter including the preceding AND
        sql = re.sub(
            r"\s+AND\s+\w+\.item_name\s+IN\s+\('<ITEM_NAME>'\)",
            "", sql, flags=re.IGNORECASE,
        )

    # ── Date placeholders ─────────────────────────────────────────────────
    if date_range:
        val       = date_range.get("value", "")
        val_lower = val.lower()

        month_map = {
            "january": "01", "february": "02", "march": "03",
            "april": "04",   "may": "05",      "june": "06",
            "july": "07",    "august": "08",    "september": "09",
            "october": "10", "november": "11",  "december": "12",
            "enero": "01",   "febrero": "02",   "marzo": "03",
            "abril": "04",   "mayo": "05",      "junio": "06",
            "julio": "07",   "agosto": "08",    "septiembre": "09",
            "octubre": "10", "noviembre": "11", "diciembre": "12",
        }
        for name, num in month_map.items():
            if name in val_lower:
                sql = sql.replace("<MM>", num)
                break

        years = re.findall(r"20\d{2}", val)

        if len(years) >= 2:
            y_start = str(min(int(years[0]), int(years[1])))
            y_end   = str(max(int(years[0]), int(years[1])))
            sql = sql.replace("<YYYY_START>", y_start)
            sql = sql.replace("<YYYY_END>",   y_end)
            # Handle templates with a single <YYYY> by expanding to IN (y1, y2, ...)
            if "<YYYY>" in sql:
                years_clause = ", ".join(f"'{y}'" for y in sorted(set(years)))
                sql = re.sub(
                    r"STRFTIME\((\w+\.doc_date),\s*'%Y'\)\s*=\s*'<YYYY>'",
                    lambda m: f"STRFTIME({m.group(1)}, '%Y') IN ({years_clause})",
                    sql,
                    flags=re.IGNORECASE,
                )
                if "<YYYY>" in sql:
                    sql = sql.replace("<YYYY>", y_start)
        elif len(years) == 1:
            sql = sql.replace("<YYYY>",       years[0])
            sql = sql.replace("<YYYY_START>", years[0])
            sql = sql.replace("<YYYY_END>",   years[0])

    if "<N>" in sql and date_range:
        val = date_range.get("value", "")
        numbers = re.findall(r"\d+", val)
        if numbers:
            sql = sql.replace("<N>", numbers[0])
            
    return sql


def _format_metric_info(metric_info: dict | None) -> str:
    """Render metric_info as a readable block for LLM prompts."""
    if not metric_info:
        return ""
    lines: list[str] = []
    if metric_info.get("metrics"):
        lines.append(f"Metric(s)         : {', '.join(metric_info['metrics'])}")
    if metric_info.get("operations"):
        lines.append(f"Operation(s)      : {', '.join(metric_info['operations'])}")
    if metric_info.get("operation_details"):
        lines.append(f"Operation details : {json.dumps(metric_info['operation_details'])}")
    if metric_info.get("filters"):
        lines.append(f"Dimension filters : {json.dumps(metric_info['filters'])}")
    return "\n".join(lines)


def _in_clause_hint(item_names: list[str] | None) -> str:
    """Build the item-filter instruction block for MEDIUM/LOW prompts."""
    if item_names:
        clause = _build_in_clause(item_names)
        n      = len(item_names)
        note   = f" (first {_IN_LIST_MAX} of {n})" if n > _IN_LIST_MAX else f" ({n} SKUs)"
        return (
            f"\nItem filter — use EXACTLY this clause{note}, "
            f"replacing any ILIKE pattern:\n  {clause}\n"
            "Do NOT use ILIKE for product matching.\n"
        )
    return "\nNo specific product filter needed — the query covers all items.\n"


# ── Public API ────────────────────────────────────────────────────────────────

def tlk_lookup_v3(
    question: str,
    item_names: list[str] | None = None,
    date_range: dict | None = None,
    metric_info: dict | None = None,
    ontology_context: dict | None = None,
) -> dict:
    """Step 4: TLK lookup with deterministic IN-based item filtering.

    Args:
        question:         The user's original question.
        item_names:       Exact item_name strings from Step 3.5.
        date_range:       Date range dict from Step 2.
        metric_info:      Dict with metrics, operations, operation_details,
                          filters — extracted from Step 2's metric result.
        ontology_context: Optional S3b output for schema-level hints.

    Returns:
        Dict: confidence, sql, source, explanation,
              similar_query_found, similarity_percent.
        confidence is one of: "ACCURATE", "MEDIUM", "LOW".
    """
    logger.info("=" * 60)
    logger.info("STEP 4 (v3): TLK LOOKUP")
    logger.info("Question    : %s", question)
    logger.info("item_names  : %d items", len(item_names or []))
    logger.info("metric_info : %s", metric_info)

    library         = _load_library()
    ddl             = _load_ddl()
    ontology_sample = _get_ontology_sample(ontology_context)
    metric_block    = _format_metric_info(metric_info)
    item_hint       = _in_clause_hint(item_names)

    best_match       = None
    match_confidence = "none"
    match_result: dict = {}

    # ── Template matching ─────────────────────────────────────────────────
    if library:
        try:
            catalog    = "\n".join(f"  #{e['id']}: {e['natural_language']}" for e in library)
            normalized = _normalize_question(question, ontology_context, date_range)

            match_prompt = f"""Given the user question and a catalog of SQL template questions, decide which template (if any) is the best match.

User question  : {question}
Normalized     : {normalized}

Analytical intent already validated upstream:
{metric_block or '(not available)'}

Template catalog:
{catalog}

Return JSON with:
- "match": "exact", "partial", or "none"
- "template_id": the #id of the best match (null if none)
- "similarity_percent": integer 0-100
- "reason": one-sentence explanation

Rules:
- Templates use <ITEM_NAME>, <MM>, <YYYY>, <YYYY_START>, <YYYY_END> as placeholders.
  Treat <ITEM_NAME> as already resolved when judging structural match.
- Use the metric and operation from the analytical intent to select the best template.
- "exact"   → template answers the same question, only placeholder values differ.
- "partial" → template is related but needs SQL adaptation.
- "none"    → no template is close enough."""

            match_result     = chat_json(match_prompt, model=MODEL_TLK,
                                         system="You are a query-matching assistant. Return only valid JSON.")
            match_confidence = match_result.get("match", "none")
            template_id      = match_result.get("template_id")

            if template_id is not None:
                tid        = str(template_id)
                best_match = next((e for e in library if str(e["id"]) == tid), None)

            logger.info("LLM match: %s (template #%s)", match_confidence, template_id)
        except Exception as exc:
            logger.warning("LLM template matching failed: %s", exc)

    # ── ACCURATE ──────────────────────────────────────────────────────────
    if match_confidence == "exact" and best_match:
        sql    = _fill_placeholders_v3(best_match["sql"], item_names, date_range)
        n_skus = len(item_names or [])
        result = {
            "confidence":          "ACCURATE",
            "sql":                 sql,
            "source":              f"TLK template #{best_match['id']} (match: exact) [v3]",
            "explanation":         (
                f"Matched TLK question: '{best_match['natural_language']}'. "
                f"Product filter resolved via IN clause ({n_skus} SKUs from S3.5)."
            ),
            "similar_query_found": f"#{best_match['id']}",
            "similarity_percent":  match_result.get("similarity_percent", 100),
        }
        logger.info("ACCURATE: %s", result["source"])
        return result

    # ── MEDIUM ────────────────────────────────────────────────────────────
    if match_confidence == "partial" and best_match:
        adapt_prompt = f"""You have a reference SQL template that partially matches the user question.
Adapt it to answer the actual question precisely.

User question:
{question}

Analytical intent (already validated — use these, do not re-infer):
{metric_block or '(not available)'}

Reference question : {best_match['natural_language']}
Reference SQL:
{best_match['sql']}

Database schema (DDL):
{ddl[:8000]}

{_TABLE_CATALOGUE}

{ontology_sample}
{item_hint}
CRITICAL business rules:
- Net billing       = SUM(inv1.line_total) - SUM(rin1.line_total)
- Net quantity sold  = SUM(inv1.quantity)  - SUM(rin1.quantity)
- Always filter cost centers: ocr_code IN ('STR01','STR02','STR03','STR04')
- Always exclude: item_name NOT LIKE '%(DO NOT USE)%'
- The item_name IN (...) clause is the COMPLETE and EXACT product filter. Do NOT add any
  additional LIKE, ILIKE, or secondary filters on item_name for any reason whatsoever.
- If the question mentions multiple product types, the IN clause already contains ALL items
  for ALL types combined. Return a single total — do NOT use UNION ALL to split them.
- Date columns are TIMESTAMP; use STRFTIME(doc_date, '%Y') for year and
  STRFTIME(doc_date, '%m') for month. Both return zero-padded strings that
  compare equal to placeholders like '<YYYY>' / '<MM>'. For a full date
  string use STRFTIME(doc_date, '%Y-%m-%d').
- Do NOT join to retail2.calendar. For seasonal queries use month ranges:
  Winter=12,01,02 | Spring=03,04,05 | Summer=06,07,08 | Autumn=09,10,11

Return ONLY the adapted SQL query, nothing else."""

        try:
            sql = chat(adapt_prompt, model=MODEL_TLK,
                       system="You are an expert SQL developer for an electronics retailer's analytics on DuckDB. Generate precise SQL.")
            sql = sql.strip().strip("`").strip()
            if sql.lower().startswith("sql"):
                sql = sql[3:].strip()
            result = {
                "confidence":          "MEDIUM",
                "sql":                 sql,
                "source":              f"Adapted from TLK #{best_match['id']} (match: partial) [v3]",
                "explanation":         "No exact template match. Adapted closest template with deterministic IN filter.",
                "similar_query_found": f"#{best_match['id']}",
                "similarity_percent":  match_result.get("similarity_percent", 0),
            }
            logger.info("MEDIUM: %s", result["source"])
            return result
        except Exception as exc:
            logger.warning("LLM adaptation failed: %s — falling through to LOW", exc)

    # ── LOW ───────────────────────────────────────────────────────────────
    gen_prompt = f"""Generate a SQL query for DuckDB to answer this question about electronics retail data.

Question:
{question}

Analytical intent (already validated — use these, do not re-infer):
{metric_block or '(not available)'}

Database schema (DDL):
{ddl[:8000]}

{_TABLE_CATALOGUE}

{ontology_sample}
{item_hint}
CRITICAL business rules:
- Net billing       = SUM(inv1.line_total) - SUM(rin1.line_total)
- Net quantity sold  = SUM(inv1.quantity)  - SUM(rin1.quantity)
- Always filter cost centers: ocr_code IN ('STR01','STR02','STR03','STR04')
- Always exclude: item_name NOT LIKE '%(DO NOT USE)%'
- The item_name IN (...) clause is the COMPLETE and EXACT product filter. Do NOT add any
  additional LIKE, ILIKE, or secondary filters on item_name for any reason whatsoever.
- If the question mentions multiple product types, the IN clause already contains ALL items
  for ALL types combined. Return a single total — do NOT use UNION ALL to split them.
- Date columns are TIMESTAMP; use STRFTIME(doc_date, '%Y') for year and
  STRFTIME(doc_date, '%m') for month. Both return zero-padded strings that
  compare equal to placeholders like '<YYYY>' / '<MM>'. For a full date
  string use STRFTIME(doc_date, '%Y-%m-%d').
- Do NOT join to retail2.calendar. For seasonal queries use month ranges:
  Winter=12,01,02 | Spring=03,04,05 | Summer=06,07,08 | Autumn=09,10,11
- Schema prefix: retail2 (e.g. retail2.inventory_stock_inv1)
- When using CTEs (WITH clauses), always reference them in a FROM clause in the final SELECT.
- Prefer the two-subquery pattern used in the reference templates over CTEs when computing a single net value.

Return ONLY the SQL query, nothing else."""

    try:
        sql = chat(gen_prompt, model=MODEL_TLK,
                   system="You are an expert SQL developer for an electronics retailer's analytics on DuckDB. Generate precise SQL.")
        sql = sql.strip().strip("`").strip()
        if sql.lower().startswith("sql"):
            sql = sql[3:].strip()
        result = {
            "confidence":          "LOW",
            "sql":                 sql,
            "source":              "Generated from scratch using DDL + ontology context [v3]",
            "explanation":         "No matching TLK template found. SQL generated with deterministic IN filter.",
            "similar_query_found": None,
            "similarity_percent":  0,
        }
        logger.info("LOW: generated from scratch")
        return result
    except Exception as exc:
        logger.error("SQL generation failed: %s", exc)
        return {
            "confidence":          "LOW",
            "sql":                 "",
            "source":              "Generation failed [v3]",
            "explanation":         f"Failed to generate SQL: {exc}",
            "similar_query_found": None,
            "similarity_percent":  0,
        }


# ── Safety wrapper ────────────────────────────────────────────────────────────

def tlk_lookup_v3_safe(
    question: str,
    item_names: list[str] | None = None,
    date_range: dict | None = None,
    metric_info: dict | None = None,
    ontology_context: dict | None = None,
) -> dict:
    """Safety wrapper around tlk_lookup_v3.

    Guard 1 — blocks execution when item_names is an empty list (S3.5
              returned 0 SKUs). Running v3 in this state would strip the
              IN filter and silently return grand totals for ALL items.

    Guard 2 — dedup placeholder (disabled; kept for future use).

    Guard 3 — complex date expressions (relative, seasonal) allow template
              matching to run normally. A warning is added only if the result
              ends up as LOW confidence.
    """
 
    n_raw = len(item_names or [])

    # Guard 1 — no SKUs surviving S3.5 → block
    if item_names is not None and len(item_names) == 0:
        return {
            "confidence":          "BLOCKED",
            "sql":                 "",
            "source":              "Blocked by safety wrapper — empty item_names",
            "explanation":         (
                "Step 3.5 returned 0 SKUs for this concept. Running v3 would "
                "strip the ILIKE filter and return grand totals across ALL items."
            ),
            "similar_query_found": None,
            "similarity_percent":  0,
            "warning":             "Empty item list — inspect S3b/S3.5 before re-running.",
        }

    # Guard 2 — dedup (currently disabled, placeholder kept for future use)
    # item_names = _dedup_item_names(item_names)

    # Guard 3 — complex date: let template matching run first, warn only if LOW
    complex_date, reason = _is_complex_date(date_range)

    result = tlk_lookup_v3(
        question=question,
        item_names=item_names,
        date_range=date_range,
        metric_info=metric_info,
        ontology_context=ontology_context,
    )

    if complex_date and result.get("confidence") == "LOW":
        result.setdefault("warning", f"Date forced LOW: {reason}")

    if item_names is not None and n_raw != len(item_names):
        prev = result.get("explanation", "")
        result["explanation"] = f"{prev}  [deduped {n_raw} → {len(item_names)} products]"

    return result

# ── Public alias ──────────────────────────────────────────────────────────────
# Expose tlk_lookup_v3_safe as the canonical entry point for external callers.
tlk_lookup = tlk_lookup_v3_safe