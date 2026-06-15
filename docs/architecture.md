# Architecture — Sevilla FC Retail Analytics v0.2.0

## Module Layout

```
src/retail_electronics/
├── __init__.py                    # Version 0.2.0
├── __main__.py                    # Starts the MCP server
├── config.py                      # Env vars, paths, constants, model configs
├── server.py                      # FastMCP server, mounts all tools
├── llm/
│   ├── __init__.py
│   └── client.py                  # OpenAI wrapper with per-step model selection
├── ontology/
│   ├── __init__.py
│   ├── index.py                   # Build in-memory search index (used by server step 3)
│   ├── search.py                  # Fuzzy/keyword ontology lookup + disambiguation
│   ├── search3.py                 # Synonym-based concept existence check (notebook S2)
│   └── translations.py            # Spanish↔English product term dictionary
└── tools/
    ├── __init__.py
    ├── classify.py                # S1: classify_question
    ├── validate.py                # S2: validate_retail_domain (two-phase + size)
    ├── validator.py               # S2 support: comprehensive dimension validator
    ├── ontology_map.py            # S3 (v1): fuzzy index mapping (server)
    ├── ontology_map2.py           # S3b (v2): sync-wrapped two-pass LLM mapping (notebooks)
    ├── sku_prefilter.py           # S3.25: deterministic size + date pre-filter
    ├── sku_filter_LLM.py          # S3.5: hybrid LLM SKU refinement
    ├── tlk_lookup.py              # S4 (v1): TLK template match (server)
    ├── tlk_lookup_v3.py           # S4 (v3): deterministic IN-clause SQL (notebooks)
    ├── execute.py                 # S5: execute_query
    └── schema.py                  # get_schema (S3 + local fallback)
```

## Two Parallel Entry Points

### MCP Server (HTTP / stdio)
The `server.py` exposes a minimal 6-tool API for MCP clients: `step1_classify_question`, `step2_validate_retail_domain`, `step3_map_to_ontology` (v1 fuzzy), `step4_tlk_lookup` (v1), `step5_execute_query`, `get_retail_schema`.

### Notebook Pipelines (direct Python imports)
Two notebooks exercise the extended pipeline without going through MCP:

| Notebook | Scope | Origin branch |
|----------|-------|---------------|
| `notebooks/full_workflow.ipynb` | S1 → S2 → S3b (3-step framework) | `origin/milan` |
| `notebooks/pipeline_full_test_fixed.ipynb` | S1 → S2 → S3b → S3.25 → S3.5 → S4 → S5 (full) | `origin/juanantonio` |

## Pipeline Diagram (extended)

```
[User Question]
       ↓
  [S1: Classify]           ──not retail──→  [Answer directly]
       ↓ sfc_retail
  [S2: Validate]           ──invalid──→  [Suggest correction]
       ↓ valid (concept, date, location, metric, size)
  [S3b: Ontology Map]      ──no match──→  [Cannot map]   (two-pass async LLM)
       ↓ matched_nodes
  [S3.25: SKU Prefilter]   deterministic — size suffix + date-window DuckDB filter
       ↓ candidate items
  [S3.5: SKU Filter]       hybrid LLM — Path A (lexical+LLM) or Path B (LLM-all ≤150)
       ↓ final item list
  [S4: TLK Lookup v3]      deterministic IN-clause SQL from item_names
       ↓
  [S5: Execute]            DuckDB query + natural-language summary
       ↓
  [Results + Confidence]
```

## MCP Tools (server.py)

| Tool | Model | Purpose |
|------|-------|---------|
| `step1_classify_question` | gpt-4o-mini | Gate: is this an SFC retail question? |
| `step2_validate_retail_domain` | gpt-4o-mini / gpt-4o | Decompose & validate concept / date / location / metric / size |
| `step3_map_to_ontology` | gpt-5.2* | v1 fuzzy index mapping (LLM only for disambiguation) |
| `step4_tlk_lookup` | o4-mini | Find/generate SQL with confidence level |
| `step5_execute_query` | gpt-4o-mini | Execute SQL + summarize results |
| `get_retail_schema` | — | Return DDL schema |

## Branch Provenance

This branch consolidates parallel work from two contributors. Files adopted from each:

| Source branch | Contribution |
|---------------|--------------|
| `origin/milan` (Milan + Elias, Apr 4 – Apr 20) | `validate.py`/`validator.py`, `search3.py`, `ontology_synonyms.json`, `ontology_metrics.json`, plus the sync wrapper + defensive prefix stripping + high-confidence filter in `ontology_map2.py`. Notebook: `full_workflow.ipynb`. |
| `origin/juanantonio` (Apr 19 – Apr 20, built on top of Milan) | Pipeline extensions S3.25 (`sku_prefilter.py`), S3.5 (`sku_filter_LLM.py`), S4 (`tlk_lookup_v3.py`). Refined `validate.py` (size extraction) and server-side `tlk_lookup.py`. Notebook: `pipeline_full_test_fixed.ipynb`. |

For files present on both branches, the `juanantonio` version generally wins (chronological superset). Exception: `ontology_map2.py` uses Milan's later `0ca6841` version because it adds the sync wrapper and quality filters.

## Ontology Index

- **Source:** `data/ontology/ontology_product.json` (fallback: dimension CSVs)
- **Size:** ~3,315 nodes (10 families + 21 subfamilies + 3,284 product types)
- **Search pipeline:** English→Spanish translation → exact → substring → fuzzy (≥0.6)
- **Startup time:** <500ms

## Confidence Levels (server step 4)

| Level | Condition | Method |
|-------|-----------|--------|
| ACCURATE | LLM finds exact template match | Fill template placeholders |
| MEDIUM | LLM finds partial template match | LLM adapts closest template |
| LOW | No match | LLM generates from DDL + ontology |

The notebook pipeline's S4 (`tlk_lookup_v3`) is deterministic and does not emit a confidence level — it builds an `IN`-clause directly from the S3.5 item list.

## Running

```bash
# MCP server (HTTP)
python -m retail_electronics

# MCP server (stdio, for Claude Desktop etc.)
pixi run python start_stdio.py

# Notebook demos
pixi run jupyter lab
#   → notebooks/full_workflow.ipynb              (S1→S2→S3b — from origin/milan)
#   → notebooks/pipeline_full_test_fixed.ipynb   (full pipeline — from origin/juanantonio)
```

## Data Dependencies

| File | Purpose |
|------|---------|
| `data/TLK/TLK_Library.json` | SQL template library (server step 4) |
| `data/retail_analytics.ddl` | Athena schema DDL |
| `data/ontology/ontology_product.json` | Product hierarchy (3-level nested JSON) |
| `data/ontology/ontology_synonyms.json` | Synonym dictionary for S2 concept validation |
| `data/ontology/ontology_metrics.json` | Metrics / dimensions / operations reference |
| `data/ontology/dim_product_family.csv` | 10 product families |
| `data/ontology/dim_product_subfamily.csv` | 21 product subfamilies |
| `data/ontology/dim_product_type.csv` | 3,284 product types |

## Static HTML docs

`docs/workflow.html` and `docs/documentation.html` are from v0.1 and do not reflect the extended pipeline. Regenerate before sharing externally.
