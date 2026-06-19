"""Step 3.25: sku_prefilter — deterministic pre-filter of the SKU pool.

Sits between S3b (ontology mapping) and S3.5 (LLM/lexical filter).
Applies a cheap, deterministic date filter BEFORE the expensive LLM pass:

  · Date filter  — keeps items whose OITM.create_date is on or before
                   the end of the requested period.

The filter is optional.  When no date_range is provided the original
item list is returned unchanged.

⚠️  Date-filter caveat: items created after the period end cannot have
existed during the period, so they are dropped.  Do NOT use this filter
for stock / availability questions outside the data range.

Public entry point:  prefilter(items, date_range, concept) → (items, meta)
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date
from functools import lru_cache

import duckdb

from retail_electronics.config import PARQUET_DIR

logger = logging.getLogger(__name__)

# ── Paths (resolved once from config) ────────────────────────────────────────

_OITM_PATH  = str(PARQUET_DIR / "master_articles_oitm.parquet")

# ── Date range helpers ────────────────────────────────────────────────────────

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

# Quarter → (first_month, last_month)
_QUARTER_MAP: dict[str, tuple[int, int]] = {
    # English
    "q1": (1, 3), "q2": (4, 6), "q3": (7, 9), "q4": (10, 12),
    "first quarter":  (1, 3),  "second quarter": (4, 6),
    "third quarter":  (7, 9),  "fourth quarter": (10, 12),
    # Spanish
    "primer trimestre":  (1, 3),  "segundo trimestre": (4, 6),
    "tercer trimestre":  (7, 9),  "cuarto trimestre":  (10, 12),
    "1er trimestre": (1, 3), "2do trimestre": (4, 6),
    "3er trimestre": (7, 9), "4to trimestre": (10, 12),
}

# Relative expressions → delta in days from today (negative = past)
_RELATIVE_MAP: list[tuple[re.Pattern, int, int]] = [
    # (pattern, start_delta_days, end_delta_days)
    (re.compile(r"last\s+(\d+)\s+months?"),   None, 0),   # handled separately
    (re.compile(r"últimos?\s+(\d+)\s+meses?"), None, 0),
    (re.compile(r"last\s+(\d+)\s+years?"),     None, 0),
    (re.compile(r"últimos?\s+(\d+)\s+años?"),  None, 0),
    (re.compile(r"last\s+year"),     -365, 0),
    (re.compile(r"último\s+año"),    -365, 0),
    (re.compile(r"this\s+year"),        0, 0),   # handled separately
    (re.compile(r"este\s+año"),         0, 0),
    (re.compile(r"this\s+month"),       0, 0),
    (re.compile(r"este\s+mes"),         0, 0),
]


def _month_end(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def _find_months(text: str) -> list[int]:
    """Return all month numbers mentioned in *text*, in order of appearance."""
    found: list[tuple[int, int]] = []  # (position, month_num)
    for name, num in _MONTH_MAP.items():
        pos = text.find(name)
        if pos != -1:
            found.append((pos, num))
    found.sort()
    return [m for _, m in found]


def _find_years(text: str) -> list[int]:
    """Return all 20xx years found in *text*, in order of appearance."""
    return [int(m) for m in re.findall(r"\b(20\d{2})\b", text)]


def _parse_date_range(date_range_str: str) -> tuple[date, date] | None:
    """Parse a natural-language date range into an inclusive (start, end) pair.

    Handles all of:
      Single month  : "december 2025", "agosto 2024"
      Single year   : "2024", "en 2023"
      Year range    : "2021-2025", "entre 2021 y 2025", "from 2021 to 2025",
                      "de 2020 a 2024"
      Month range   : "from january to march 2024", "de enero a marzo de 2024"
      Quarters      : "Q1 2024", "primer trimestre 2023"
      ISO date      : "2025-12-01"
      Relative      : "last 3 months", "últimos 6 meses", "last year",
                      "this year", "this month"

    Returns None if nothing can be parsed.
    """
    today = date.today()
    text  = date_range_str.lower().strip()

    # ── 1. Full ISO date  2025-12-01 ────────────────────────────────────
    iso_m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if iso_m:
        try:
            d = date(int(iso_m[1]), int(iso_m[2]), int(iso_m[3]))
            return d, d
        except ValueError:
            pass

    years  = _find_years(text)
    months = _find_months(text)

    # ── 2. Relative expressions ──────────────────────────────────────────

    # "last N months" / "últimos N meses"
    for pat in (re.compile(r"last\s+(\d+)\s+months?"),
                re.compile(r"últimos?\s+(\d+)\s+meses?")):
        m = pat.search(text)
        if m:
            n = int(m.group(1))
            start = today - __import__("datetime").timedelta(days=n * 30)
            return start, today

    # "last N years" / "últimos N años"
    for pat in (re.compile(r"last\s+(\d+)\s+years?"),
                re.compile(r"últimos?\s+(\d+)\s+años?")):
        m = pat.search(text)
        if m:
            n = int(m.group(1))
            return date(today.year - n, today.month, today.day), today

    # "last year" / "último año"
    if re.search(r"\blast\s+year\b", text) or re.search(r"\búltimo\s+año\b", text):
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)

    # "this year" / "este año"
    if re.search(r"\bthis\s+year\b", text) or re.search(r"\beste\s+año\b", text):
        return date(today.year, 1, 1), today

    # "this month" / "este mes"
    if re.search(r"\bthis\s+month\b", text) or re.search(r"\beste\s+mes\b", text):
        return date(today.year, today.month, 1), today

    # ── 3. Quarter  "Q1 2024" / "primer trimestre 2023" ─────────────────
    for q_key, (q_start, q_end) in _QUARTER_MAP.items():
        if q_key in text:
            y = years[0] if years else today.year
            return date(y, q_start, 1), _month_end(y, q_end)

    # ── 4. Year range  "2021-2025" / "entre 2021 y 2025" ────────────────
    #    Detect two distinct years in the string.
    if len(years) >= 2:
        y_start, y_end = min(years[0], years[1]), max(years[0], years[1])

        # Month range across years: "january 2023 to march 2024"
        if len(months) >= 2:
            m_start, m_end = months[0], months[-1]
            return date(y_start, m_start, 1), _month_end(y_end, m_end)

        # Pure year range
        return date(y_start, 1, 1), date(y_end, 12, 31)

    # ── 5. Single year with optional month range ─────────────────────────
    if len(years) == 1:
        y = years[0]

        if len(months) >= 2:
            # "from january to march 2024" / "de enero a marzo de 2024"
            m_start, m_end = months[0], months[-1]
            if m_start <= m_end:
                return date(y, m_start, 1), _month_end(y, m_end)

        if len(months) == 1:
            # "august 2024"
            m = months[0]
            return date(y, m, 1), _month_end(y, m)

        # Plain year: "2024"
        return date(y, 1, 1), date(y, 12, 31)

    # ── 6. Month(s) without a year — assume current year ────────────────
    if len(months) >= 2:
        m_start, m_end = months[0], months[-1]
        if m_start <= m_end:
            return date(today.year, m_start, 1), _month_end(today.year, m_end)

    if len(months) == 1:
        m = months[0]
        return date(today.year, m, 1), _month_end(today.year, m)

    return None


# ── Date filter ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _get_conn() -> duckdb.DuckDBPyConnection:
    """Cached read-only DuckDB connection for the OITM parquet."""
    conn = duckdb.connect(":memory:")
    conn.execute(
        f"CREATE VIEW oitm AS "
        f"SELECT item_name, create_date FROM read_parquet('{_OITM_PATH}')"
    )
    return conn


def filter_by_date_range(
    items: list[dict],
    date_range_str: str,
) -> tuple[list[dict], dict]:
    """Keep only items that could have existed during *date_range_str*.

    Logic:
      An item created AFTER the end of the requested period cannot have been
      sold during that period.  We therefore keep only items whose
      OITM.create_date <= period_end.

      This is a single-table filter on OITM — no join to INV1 required.
      It is always conservative (never falsely removes a valid item) and
      works correctly even when S3b returns ontology nodes that span
      multiple catalog eras.

    Args:
        items:          item dicts with 'item_str' key.
        date_range_str: natural-language date range, e.g. "december 2025".

    Returns:
        (filtered_items, meta_dict)
    """
    if not date_range_str or not date_range_str.strip():
        return items, {"applied": False, "reason": "no date range specified"}

    date_pair = _parse_date_range(date_range_str)
    if not date_pair:
        return items, {
            "applied": False,
            "reason": f"could not parse date range: '{date_range_str}'",
        }

    start_dt, end_dt = date_pair
    logger.info("Date pre-filter: %s → [%s, %s]", date_range_str, start_dt, end_dt)

    item_names_list = [it["item_str"] for it in items]
    if not item_names_list:
        return [], {"applied": True, "before": 0, "after": 0, "reason": "empty input"}

    def _esc(s: str) -> str:
        return s.replace("'", "''")

    names_sql = ", ".join(f"'{_esc(n)}'" for n in item_names_list)

    # Keep items whose create_date is on or before the end of the period.
    # Items created after end_dt did not exist yet and cannot have been sold.
    sql = f"""
        SELECT DISTINCT item_name
        FROM oitm
        WHERE item_name IN ({names_sql})
          AND CAST(create_date AS DATE) <= DATE '{end_dt}'
    """

    try:
        conn         = _get_conn()
        result       = conn.execute(sql).fetchdf()
        valid_names  = set(result["item_name"].tolist())
    except Exception as exc:
        logger.warning("Date pre-filter query failed: %s — skipping filter", exc)
        return items, {"applied": False, "reason": f"query error: {exc}"}

    matched  = [it for it in items if it["item_str"] in valid_names]
    n_before = len(items)
    n_after  = len(matched)

    meta = {
        "applied": True,
        "date_range": date_range_str,
        "start": str(start_dt),
        "end": str(end_dt),
        "before": n_before,
        "after": n_after,
    }
    logger.info(
        "Date pre-filter [create_date <= %s]: %d → %d items",
        end_dt, n_before, n_after,
    )
    return matched, meta


# ── Public entry point ────────────────────────────────────────────────────────

def prefilter(
    items: list[dict],
    date_range: str | None = None,
    concept: str | None = None,
) -> tuple[list[dict], dict]:
    """Step 3.25: deterministic pre-filter before the S3.5 LLM/lexical pass.

    Applies a single filter:
      · Date filter  — DuckDB query on OITM.create_date

    The filter is skipped when date_range is None/empty.  In that case the
    original list is returned unchanged.

    Args:
        items:      Item pool from S3b.  Each dict has at minimum:
                    {'item_str': str, 'family': str, 'subfamily': str,
                     'product_type': str}
        date_range: Date range string from validate, e.g. "december 2025".
        concept:    Full concept string from S2 (main + attribute), e.g.
                    "wireless headphones". Stored in meta for downstream tracing.

    Returns:
        (filtered_items, meta)

        meta keys:
          original_count  — items entering the pre-filter
          final_count     — items leaving the pre-filter
          reduction       — items removed (original - final)
          date_applied    — True if the date filter ran
          date_meta       — detailed date filter stats
    """
    original_count = len(items)
    logger.info(
        "=" * 60 + "\nSTEP 3.25: SKU PRE-FILTER"
        "\n  items in : %d | date_range=%s | concept=%s",
        original_count, date_range, concept,
    )

    date_meta: dict = {}

    # Date filter (DuckDB query on OITM.create_date)
    if date_range:
        items, date_meta = filter_by_date_range(items, date_range)

    final_count = len(items)
    meta = {
        "original_count": original_count,
        "final_count": final_count,
        "reduction": original_count - final_count,
        "date_applied": bool(date_meta.get("applied")),
        "date_meta": date_meta,
        "concept": concept,
    }
    logger.info(
        "Pre-filter done: %d → %d items (−%d) | date=%s",
        original_count, final_count, original_count - final_count,
        meta["date_applied"],
    )
    return items, meta