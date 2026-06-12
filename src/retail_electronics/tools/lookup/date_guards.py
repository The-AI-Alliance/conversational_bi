"""P3 date-complexity guards for tlk_lookup.

Detects multi-year, relative, and seasonal date expressions that tlk_lookup_v3's
placeholder-fill logic cannot safely handle. When detected, tlk_lookup forces the
LOW path so the LLM regenerates SQL from the full date text.
"""

from __future__ import annotations

import re

_RELATIVE_RE = re.compile(
    r"\b(last|past|previous|ultim|ultima|ultimo)\b.*\b(day|week|month|year|dia|semana|mes|año|ano)s?\b",
    re.IGNORECASE,
)
_SEASON_RE = re.compile(
    r"\b(winter|summer|spring|autumn|fall|invierno|verano|primavera|otono|otoño|temporada|q[1-4])\b",
    re.IGNORECASE,
)


def _is_complex_date(date_range: dict | None) -> tuple[bool, str]:
    """Return (True, reason) if the date_range requires LOW-path SQL generation.

    A date is "complex" when tlk_lookup_v3's placeholder-fill would produce
    wrong SQL:
      - Relative:  "last 3 months" — no YYYY-MM-DD translation available
      - Seasonal:  "Winter 2023" — no month-range mapping in v3
    """
    if not date_range:
        return False, ""
    val = (date_range.get("value") or "").strip()
    if not val or val == "not specified":
        return False, ""
    if _RELATIVE_RE.search(val):
        return True, "relative date — v3 has no translation to YYYY-MM-DD"
    if _SEASON_RE.search(val):
        return True, "season/quarter — v3 only knows month names"
    return False, ""
