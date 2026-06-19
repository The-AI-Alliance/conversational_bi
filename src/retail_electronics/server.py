"""FastMCP server — 7-stage retail workflow tools + get_schema."""

import asyncio
import logging
import uuid

from fastmcp import FastMCP

from retail_electronics.ontology.index import get_index
from retail_electronics.tools.classify.classify import classify_question
from retail_electronics.tools.display.display import (
    display_s3,
    display_s325,
    display_s35,
    display_s4,
)
from retail_electronics.tools.execute.execute import execute_query
from retail_electronics.tools.lookup.tlk import tlk_lookup
from retail_electronics.tools.ontology.map import map_to_ontology
from retail_electronics.tools.schema.schema import get_schema
from retail_electronics.tools.sku.filter_llm import _get_items_for_nodes, _load_ontology, sku_filter
from retail_electronics.tools.sku.prefilter import prefilter
from retail_electronics.tools.validate.validate import validate_retail_domain

logger = logging.getLogger(__name__)

mcp = FastMCP("Electronics Retail Analytics")

# ── SQL store — avoids sending large SQL payloads over MCP ───────────────────
# SQL is generated in step3_to_4_pipeline, stored here by ID, and retrieved
# by step5_execute_query. The SQL never travels over the MCP protocol.
_sql_store: dict[str, str] = {}


def _store_sql(sql: str) -> str:
    """Store SQL in memory and return its ID."""
    sql_id = str(uuid.uuid4())
    _sql_store[sql_id] = sql
    return sql_id


# ── Workflow Tools ───────────────────────────────────────────────────────────

@mcp.tool()
def step1_classify_question(question: str) -> dict:
    """Step 1: Classify whether a question is about electronics retail, electronics non-retail, or general knowledge.

    This is the entry point of the 7-step validation workflow.
    - electronics_retail: proceeds to Step 2
    - electronics_non_retail / general: answers directly and exits

    Args:
        question: The user's natural language question.

    Returns:
        classification (electronics_retail|electronics_non_retail|general), reasoning, and optional direct answer.
    """
    return classify_question(question)


@mcp.tool()
def step2_validate_retail_domain(question: str) -> dict:
    """Step 2: Validate that a retail question is answerable within the electronics retail domain.

    Decomposes the question into concept, metric, date_range, location, and size,
    validating each against known constraints (electronics products, valid dates 2020-today,
    real locations). Also extracts metric_info for use in Step 4.

    Args:
        question: The user's question (already classified as electronics_retail).

    Returns:
        is_valid flag, per-dimension validation, size, metric (with metrics/operations/
        operation_details/filters), and optional correction suggestion.
    """
    return validate_retail_domain(question)

@mcp.tool()
async def step3_to_4_pipeline(
    concepts: list[str],
    question: str,
    date_range: dict | None = None,
    metric_info: dict | None = None,
) -> dict:
    """Steps 3→4 unified: ontology map + prefilter + SKU filter + SQL generation.

    Runs the full heavy pipeline server-side in a single tool call to avoid
    Claude Desktop timeouts. Replaces calling step3_map_to_ontology,
    step3_25_sku_prefilter, step3_5_sku_filter and step4_tlk_lookup separately.

    Args:
        concepts:    List of product concept strings from Step 2 (all valid concepts).
        question:    Original user question.
        date_range:  date_range dict from Step 2.
        metric_info: metric dict from Step 2.
    """
    # ── S3: map all concepts ──────────────────────────────────────────────
    all_matched_nodes: list = []
    seen_paths: set = set()
    s3_displays: list = []
    s3_last: dict = {}

    for concept in concepts:
        res = await map_to_ontology(concept, question)
        s3_last = res
        s3_displays.append(display_s3(res))
        for node in res.get("matched_nodes", []):
            if node["path"] not in seen_paths:
                seen_paths.add(node["path"])
                all_matched_nodes.append(node)

    s3 = {**s3_last, "matched_nodes": all_matched_nodes}

    if concepts and not all_matched_nodes:
        return {
            "blocked": True,
            "stage": "S3",
            "reason": "No ontology nodes matched.",
            "display": "\n".join(s3_displays),
            "sql": "",
            "confidence": "BLOCKED",
        }

    # ── S3.25 + S3.5: prefilter + SKU filter ─────────────────────────────
    item_names = None
    s325_display = ""
    s35_display = ""

    if all_matched_nodes:
        concept_full = " and ".join(concepts) if concepts else None

        # Bug 3 fix: only pass date value when is_valid=True
        date_str = (
            date_range.get("value")
            if isinstance(date_range, dict) and date_range.get("is_valid")
            else None
        )

        ontology = _load_ontology()
        items = _get_items_for_nodes(ontology, all_matched_nodes)
        filtered_items, meta = prefilter(items, date_str, concept_full)
        s325_result = {"items": filtered_items, "meta": meta}
        s325_display = display_s325(s325_result)

        if concept_full and filtered_items:
            s35_result = sku_filter(
                concept_full,
                all_matched_nodes,
                question=question,
                items_override=filtered_items,
            )
            s35_display = display_s35(s35_result)
            item_names = s35_result.get("item_names", [])

    # ── S4: TLK lookup ────────────────────────────────────────────────────
    s4_result = tlk_lookup(question, item_names, date_range, metric_info, s3)
    s4_display = display_s4(s4_result)

    combined_display = "\n".join(filter(None, [
        *s3_displays, s325_display, s35_display, s4_display,
    ]))

    return {
        "sql_id":              _store_sql(s4_result.get("sql", "")),
        "confidence":          s4_result.get("confidence", "LOW"),
        "source":              s4_result.get("source", ""),
        "explanation":         s4_result.get("explanation", ""),
        "warning":             s4_result.get("warning"),
        "similar_query_found": s4_result.get("similar_query_found"),
        "similarity_percent":  s4_result.get("similarity_percent", 0),
        "matched_nodes_count": len(all_matched_nodes),
        "display": combined_display,
    }

@mcp.tool()
def step5_execute_query(confidence: str, question: str, sql: str = "", sql_id: str = "") -> dict:
    """Step 5: Execute SQL against local parquet via DuckDB and summarize results.

    Runs the query, then uses LLM to generate a natural language summary.
    Prepends a warning if confidence is LOW.

    Args:
        confidence: ACCURATE, MEDIUM, or LOW from Step 4.
        question:   Original question for summary context.
        sql:        SQL query string. Pass either sql or sql_id, not both.
        sql_id:     ID returned by step3_to_4_pipeline. Preferred over sql
                    to avoid large payloads over MCP.

    Returns:
        results_csv, row_count, natural language summary, confidence badge, and optional warning.
    """
    if sql_id:
        sql = _sql_store.pop(sql_id, sql)
    return execute_query(sql, confidence, question)


# ── Utility Tools ────────────────────────────────────────────────────────────

@mcp.tool()
def get_retail_schema(product: str) -> str:
    """Return the DDL schema for the given product (reads from local DDL file).

    Args:
        product: The product name. Currently supported: retail_analytics

    Returns:
        DDL string for the given product.
    """
    return get_schema(product)


# ── Server lifecycle ─────────────────────────────────────────────────────────

def build_index() -> None:
    """Pre-build the ontology index at server startup."""
    logger.info("Building ontology index...")
    idx = get_index()
    logger.info("Index ready: %d nodes", len(idx.nodes))


def create_server() -> FastMCP:
    """Create and configure the MCP server."""
    logging.basicConfig(
        format="[%(levelname)s] %(name)s: %(message)s",
        level=logging.INFO,
    )
    build_index()
    return mcp