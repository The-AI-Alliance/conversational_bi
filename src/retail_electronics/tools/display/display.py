"""Rich display helpers for MCP tool responses.

Each public function takes a stage's output dict and returns a formatted
multi-line string. These strings are embedded as the `display` field in every
tool response so both notebook users and Claude (via direct MCP) see rich output.
"""

from __future__ import annotations

SEP  = '═' * 72   # ════════
THIN = '─' * 72   # ────────

_CONF_ICONS = {
    'ACCURATE': '\U0001f7e2',   # 🟢
    'MEDIUM':   '\U0001f7e1',   # 🟡
    'LOW':      '\U0001f534',   # 🔴
    'BLOCKED':  '⛔',       # ⛔
}

_LLM_ALL_SIG_THRESHOLD = 10_000   # must match filter_llm.py


# ── Internal helpers ──────────────────────────────────────────────────────────

def _hdr(tag: str, detail: str = '') -> str:
    line = f'  [{tag}]'
    if detail:
        line += f'  {detail}'
    return f'\n{SEP}\n{line}\n{THIN}'


def _trunc(s: str, n: int = 100) -> str:
    return s[:n] + '…' if len(s) > n else s


# ── Per-stage display functions ───────────────────────────────────────────────

def display_s1(s1: dict) -> str:
    lines = [_hdr('S1', 'CLASSIFY')]
    lines.append(f'  Classification : {s1.get("classification", "?")}')
    lines.append(f'  Reasoning      : {_trunc(s1.get("reasoning", ""), 120)}')
    if s1.get('answer'):
        lines.append(f'  Answer         : {_trunc(s1["answer"], 120)}')
    return '\n'.join(lines)


def display_s2(s2: dict) -> str:
    lines = [_hdr('S2', 'VALIDATE')]

    overall = '✅ VALID' if s2.get('is_valid') else '❌ INVALID'   # ✅ ❌
    lines.append(f'  {overall}')

    # Concept
    concept = s2.get('concept', {})
    items = concept.get('items', [])
    if items:
        for it in items:
            icon = '✓' if it.get('is_valid') else '✗'   # ✓ ✗
            val  = it.get('value') or it.get('main') or '?'
            rsn  = _trunc(it.get('reason', ''), 80)
            lines.append(f'  {icon} concept  : {val}  ({rsn})')
    else:
        icon = '✓' if concept.get('is_valid', True) else '✗'
        lines.append(f'  {icon} concept  : {concept.get("values", ["none"])[0] if concept.get("values") else "none"}')

    # Date
    dr = s2.get('date_range', {})
    icon = '✓' if dr.get('is_valid', True) else '✗'
    lines.append(f'  {icon} date     : {dr.get("value", "not specified")}')

    # Location
    loc = s2.get('location', {})
    icon = '✓' if loc.get('is_valid', True) else '✗'
    lines.append(f'  {icon} location : {loc.get("value", "not specified")}')

    # Metric
    metric = s2.get('metric', {})
    icon = '✓' if metric.get('is_valid', True) else '✗'
    metrics_list  = metric.get('metrics', [])
    ops_list      = metric.get('operations', [])
    metric_str    = ', '.join(metrics_list) if metrics_list else '?'
    ops_str       = f'  [{", ".join(ops_list)}]' if ops_list else ''
    verdict       = metric.get('verdict', '')
    lines.append(f'  {icon} metric   : {metric_str}{ops_str}  verdict={verdict}')
    if not metric.get('is_valid'):
        lines.append(f'    reason: {_trunc(metric.get("reason", ""), 100)}')

    # Size (pass-through, no validation)
    size = s2.get('size')
    if size:
        lines.append(f'  • size     : {size}  (pass-through)')

    # Suggestion
    if s2.get('suggestion'):
        lines.append(f'\n  Suggestion : {_trunc(s2["suggestion"], 120)}')

    return '\n'.join(lines)


def display_s3(s3: dict) -> str:
    via    = s3.get('via', '')
    detail = f'ONTOLOGY MAP  [via={via}]' if via else 'ONTOLOGY MAP'
    lines  = [_hdr('S3b', detail)]

    nodes = s3.get('matched_nodes', [])
    gran  = s3.get('granularity', 'none')
    lines.append(f'  Matched nodes : {len(nodes)}  (granularity={gran})')
    for n in nodes:
        lines.append(f'    · {n.get("path", "?")}  ({n.get("sku_count", "?")} SKUs)')

    item_matches = s3.get('item_matches', [])
    if item_matches:
        lines.append(f'\n  Item matches  : {len(item_matches)}')
        for m in item_matches[:5]:
            lines.append(f'    · {m.get("item_name", "?")}  [{m.get("item_code", "")}]')
        if len(item_matches) > 5:
            lines.append(f'    ... +{len(item_matches) - 5} more')

    return '\n'.join(lines)


def display_s325(s325: dict) -> str:
    lines = [_hdr('S3.25', 'SKU PRE-FILTER')]
    meta  = s325.get('meta', {})
    items = s325.get('items', [])

    orig  = meta.get('original_count', 0)
    final = meta.get('final_count', len(items))
    red   = meta.get('reduction', orig - final)
    pct   = (red / orig * 100) if orig else 0

    lines.append(f'  Items in   : {orig}')

    # Size filter
    sm = meta.get('size_meta', {})
    if meta.get('size_applied') and sm.get('applied'):
        skip = sm.get('skipped_no_token', 0)
        lines.append(
            f'  Size={sm.get("query_size", "?")!r:<6}  : '
            f'{sm.get("before", 0)} → {sm.get("after", 0)}'   # →
            f'  (−{sm.get("before", 0) - sm.get("after", 0)}'
            f'  skipped_no_token={skip})'
        )
    else:
        lines.append('  Size       : not applied')

    # Date filter
    dm = meta.get('date_meta', {})
    if meta.get('date_applied') and dm.get('applied'):
        lines.append(f'  Date       : {dm.get("start", "?")} – {dm.get("end", "?")}')
        lines.append(
            f'               {dm.get("before", 0)} → {dm.get("after", 0)}'
            f'  (−{dm.get("before", 0) - dm.get("after", 0)})'
        )
    else:
        lines.append('  Date       : not applied')

    lines.append(f'  Items out  : {final}  (−{red} = {pct:.0f}% reduction)')

    if meta.get('warning'):
        lines.append(f'\n  ⚠  {meta["warning"]}')

    return '\n'.join(lines)


def display_s35(s35: dict) -> str:
    lines = [_hdr('S3.5', 'SKU FILTER LLM')]

    path_lbl = 'LLM-all (Path B)' if s35.get('path') == 'B' else 'lexical + LLM (Path A)'
    lines.append(f'  Path           : {s35.get("path", "?")}  ({path_lbl})')
    lines.append(
        f'  Sigs → LLM    : {s35.get("sent_to_llm", 0)}'
        f'  (threshold={_LLM_ALL_SIG_THRESHOLD})'
    )

    total_in  = s35.get('total_input', 0)
    total_out = s35.get('total_matched', 0)
    pct       = (total_out / total_in * 100) if total_in else 0

    # Unique kept/removed sigs
    kept_sigs    = s35.get('kept_sigs', [])
    removed_sigs = s35.get('removed_sigs', [])

    kept_sig_str    = f'  /  {len(kept_sigs)} unique sigs' if kept_sigs else ''
    removed_sig_str = f'  /  {len(removed_sigs)} unique sigs' if removed_sigs else ''

    lines.append(f'  Input items    : {total_in}')
    lines.append(f'  ✅ Kept        : {total_out}  ({pct:.0f}%){kept_sig_str}')
    lines.append(
        f'  \U0001f5d1  Removed    : {total_in - total_out}'   # 🗑
        f'  ({100 - pct:.0f}%){removed_sig_str}'
    )

    if removed_sigs:
        lines.append(f'\n  Removed products (up to 8):')
        for sig in removed_sigs[:8]:
            lines.append(f'    – {sig}')   # –
        if len(removed_sigs) > 8:
            lines.append(f'    ... +{len(removed_sigs) - 8} more')

    lines.append(f'\n  LLM time  : {s35.get("time_llm_s", 0):.3f}s')

    item_names = s35.get('item_names', [])
    if item_names:
        lines.append(f'\n  Items sent to S4 : {len(item_names)} SKUs')

    if s35.get('warning'):
        lines.append(f'\n  ⚠  {s35["warning"]}')

    return '\n'.join(lines)


def display_s4(s4: dict) -> str:
    lines = [_hdr('S4', 'TLK LOOKUP')]

    conf = s4.get('confidence', '?')
    icon = _CONF_ICONS.get(conf, '')
    lines.append(f'  Confidence  : {icon} {conf}')
    lines.append(f'  Source      : {s4.get("source", "?")}')
    lines.append(f'  Similarity  : {s4.get("similarity_percent", 0)}%')
    lines.append(f'  Explanation : {_trunc(s4.get("explanation", ""), 120)}')

    if s4.get('warning'):
        lines.append(f'\n  ⚠  {s4["warning"]}')

    sql = s4.get('sql', '')
    if sql:
        lines.append(f'\n  SQL length  : {len(sql)} chars  ({sql.count(chr(10))+1} lines)')

    return '\n'.join(lines)


def display_s5(s5: dict) -> str:
    lines = [_hdr('S5', 'EXECUTE')]

    if s5.get('warning'):
        lines.append(f'  ⚠  {s5["warning"]}')

    lines.append(f'  Rows returned : {s5.get("row_count", 0)}')
    lines.append(f'  Summary       : {s5.get("summary", "")}')

    csv = s5.get('results_csv', '')
    if csv and s5.get('row_count', 0) > 0:
        lines.append('\n  Raw results (CSV):')
        csv_lines = csv.splitlines()
        for row in csv_lines[:15]:
            lines.append(f'    {row}')
        if len(csv_lines) > 15:
            lines.append(f'    ... +{len(csv_lines) - 15} more rows')

    return '\n'.join(lines)