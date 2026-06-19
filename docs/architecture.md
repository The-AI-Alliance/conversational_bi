# Architecture — Retail Electronics Analytics v0.2.0

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
│   ├── index.py                   # Build in-memory search index (used by step 3)
│   └── search3.py                 # Synonym-based concept existence check
└── tools/
    ├── __init__.py
    ├── classify/
    │   └── classify.py            # Step 1: classify_question
    ├── validate/
    │   ├── validate.py            # Step 2: validate_retail_domain
    │   └── validator.py           # Step 2 support: comprehensive dimension validator
    ├── ontology/
    │   └── map.py                 # Step 3: ontology mapping
    ├── lookup/
    │   ├── date_guards.py         # Step 3.25 support: date complexity checks
    │   └── tlk.py                 # Step 4: TLK template lookup
    ├── sku/
    │   ├── prefilter.py           # Step 3.25: deterministic date pre-filter
    │   └── filter_llm.py          # Step 3.5: hybrid LLM SKU refinement
    ├── execute/
    │   └── execute.py             # Step 5: execute_query
    ├── display/
    │   └── display.py             # Formats intermediate step output for display
    └── schema/
        └── schema.py               # get_schema (reads DDL)
```

## MCP Server (HTTP / stdio)

`server.py` exposes the workflow as FastMCP tools:

| Tool | Model | Purpose |
|------|-------|---------|
| `step1_classify_question` | gpt-4o-mini | Gate: is this an electronics retail question? |
| `step2_validate_retail_domain` | gpt-4o-mini / gpt-4o | Decompose & validate concept / date / location / metric / size |
| `step3_to_4_pipeline` | gpt-5.1 / o4-mini | Unified: ontology map → date prefilter → LLM SKU filter → TLK lookup → SQL |
| `step5_execute_query` | gpt-4o-mini | Execute SQL via DuckDB + summarize results |
| `get_retail_schema` | — | Return DDL schema |

Steps 3 through 4 are wired into a single tool (`step3_to_4_pipeline`) to avoid client-side timeouts on multi-call MCP clients — internally it still runs each stage in order.

## Pipeline Diagram

```
[User Question]
       ↓
  [Step 1: Classify]        ──non-retail / general──→  [Answer directly]
       ↓ electronics_retail
  [Step 2: Validate]        ──invalid──→  [Suggest correction]
       ↓ valid (concept, date, location, metric, size)
  [Step 3: Ontology Map]    ──no match──→  [Cannot map]
       ↓ matched_nodes
  [Step 3.25: Date Prefilter]   deterministic — keeps items created on/before the requested period
       ↓ candidate items
  [Step 3.5: LLM SKU Filter]        hybrid LLM refinement of candidate items
       ↓ final item list
  [Step 4: TLK Lookup]      deterministic IN-clause SQL from item_names
       ↓
  [Step 5: Execute]         DuckDB query + natural-language summary
       ↓
  [Results + Confidence]
```

## Confidence Levels (Step 4)

| Level | Condition | Method |
|-------|-----------|--------|
| ACCURATE | LLM finds exact template match | Fill template placeholders |
| MEDIUM | LLM finds partial template match | LLM adapts closest template |
| LOW | No match | LLM generates SQL from DDL + ontology context |

## Ontology Index

- **Source:** `data/ontology/ontology_product.json`
- **Size:** 7 families → 29 subfamilies → 95 product types
- **Search pipeline:** exact → substring → fuzzy (≥0.6)

## Running

```bash
# MCP server (HTTP)
python -m retail_electronics

# MCP server (stdio, for Claude Desktop etc.)
pixi run python start_stdio.py
```

## Data Dependencies

| File | Purpose |
|------|---------|
| `data/TLK/TLK_Library.json` | SQL template library (Step 4) |
| `data/retail_analytics.ddl` | DuckDB schema DDL |
| `data/ontology/ontology_product.json` | Product hierarchy (3-level nested JSON) |
| `data/ontology/ontology_product_final.json` | Refined product hierarchy used by Step 3 |
| `data/ontology/ontology_synonyms.json` | Synonym dictionary for Step 2 concept validation |
| `data/ontology/ontology_metrics.json` | Metrics / dimensions / operations reference |
| `data/ontology/synonyms.json` | Synonym lookup used by `search3.py` |
