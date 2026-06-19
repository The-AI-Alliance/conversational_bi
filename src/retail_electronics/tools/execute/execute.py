"""Step 5: execute_query — run SQL via DuckDB on local parquet files."""

import logging

import duckdb

from retail_electronics.config import MODEL_SUMMARIZE, PARQUET_DIR
from retail_electronics.llm.client import chat
from retail_electronics.tools.display.display import display_s5

logger = logging.getLogger(__name__)

_conn: duckdb.DuckDBPyConnection | None = None


def _get_connection() -> duckdb.DuckDBPyConnection:
    """Return a cached in-memory DuckDB connection with parquet views."""
    global _conn
    if _conn is not None:
        return _conn

    _conn = duckdb.connect(":memory:")
    _conn.execute("CREATE SCHEMA IF NOT EXISTS retail")
    _conn.execute("CREATE SCHEMA IF NOT EXISTS retail2")

    for pq in sorted(PARQUET_DIR.glob("*.parquet")):
        view_name = pq.stem  # e.g. "master_articles_oitm"
        try:
            _conn.execute(
                f"CREATE VIEW retail.{view_name} AS "
                f"SELECT * FROM read_parquet('{pq}')"
            )
            _conn.execute(
                f"CREATE VIEW retail2.{view_name} AS "
                f"SELECT * FROM read_parquet('{pq}')"
            )
            logger.debug("Registered view: %s → %s", view_name, pq.name)
        except Exception as e:
            logger.warning("Skipping %s: %s", pq.name, e)

    logger.info(
        "DuckDB connection ready: %d parquet files registered",
        len(list(PARQUET_DIR.glob("*.parquet"))),
    )
    return _conn


def execute_query(sql: str, confidence: str, question: str) -> dict:
    """Execute SQL against local parquet via DuckDB, then summarize.

    Args:
        sql: Valid SQL statement for the retail schema.
        confidence: ACCURATE, MEDIUM, or LOW.
        question: Original user question for context in summary.

    Returns:
        dict with results_csv, row_count, summary, confidence, warning.
    """
    logger.info("=" * 60)
    logger.info("STEP 5: EXECUTE QUERY")
    logger.info("Confidence: %s", confidence)
    logger.info("SQL: %s", sql)

    warning = None
    if confidence == "LOW":
        warning = (
            "⚠️ LOW CONFIDENCE: This SQL was generated from scratch "
            "without a verified template. Results may be inaccurate."
        )
        logger.warning(warning)

    # Execute SQL
    try:
        sql_clean = sql.replace("–", "-").replace("—", "-")
        conn = _get_connection()
        results_df = conn.execute(sql_clean).fetchdf()
        results_csv = results_df.to_csv(index=False)
        row_count = len(results_df)
        logger.info("Query executed: %d rows returned", row_count)
    except Exception as e:
        msg = f"Query execution failed: {e}"
        logger.error(msg)
        err_result = {
            "results_csv": "",
            "row_count": 0,
            "summary": msg,
            "confidence": confidence,
            "warning": warning,
        }
        err_result['display'] = display_s5(err_result)
        return err_result

    # Summarize results with LLM
    try:
        csv_preview = "\n".join(results_csv.split("\n")[:50])
        summary_prompt = f"""Summarize the following SQL query results in natural language.
Be concise and specific. Include key numbers.

Original question: {question}
Confidence level: {confidence}
Row count: {row_count}

Results (CSV):
{csv_preview}
"""
        summary = chat(
            summary_prompt,
            model=MODEL_SUMMARIZE,
            system="You are a retail analytics assistant for an electronics retailer. Summarize query results clearly and concisely in 2-3 sentences. Use EUR for monetary values.",
        )
        logger.info("Summary: %s", summary)
    except Exception as e:
        logger.warning("Summary generation failed: %s", e)
        summary = f"Query returned {row_count} rows. (Summary unavailable)"

    result = {
        "results_csv": results_csv,
        "row_count": row_count,
        "summary": summary,
        "confidence": confidence,
        "warning": warning,
    }
    result['display'] = display_s5(result)
    return result
