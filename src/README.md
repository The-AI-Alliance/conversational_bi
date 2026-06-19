_Last edited: 2026-04-07_

# Sevilla FC Retail Analytics

> MCP server that answers natural language questions about Sevilla FC retail operations via a 5-step validation pipeline.

## Overview

The server receives a retail question in plain language, classifies and validates it, maps the product concept to the internal ontology, looks up or generates the SQL query from a template library (TLK), and executes it against parquet data via DuckDB — returning results with a confidence badge (`ACCURATE`, `MEDIUM`, or `LOW`).

Built with [FastMCP](https://github.com/jlowin/fastmcp), OpenAI models, and managed with [Pixi](https://pixi.sh).

---

## 5-Step Pipeline

```
Question
  │
  ▼
Step 1 · Classify      — sfc_retail | sfc_non_retail | general
  │
  ▼ (sfc_retail only)
Step 2 · Validate      — concept / date_range / location dimensions
  │
  ▼
Step 3 · Ontology Map  — fuzzy index with LLM disambiguation
  │
  ▼
Step 4 · TLK Lookup    — ACCURATE (template match) / MEDIUM (adapt) / LOW (generate)
  │
  ▼
Step 5 · Execute       — DuckDB query + LLM natural language summary
```

See [`docs/architecture.md`](docs/architecture.md) for full detail and [`docs/workflow.html`](docs/workflow.html) for an interactive diagram.

---

## MCP Tools

| Tool | Step | Description | Model |
|------|------|-------------|-------|
| `step1_classify_question` | 1 | Classify question scope | `gpt-4o-mini` |
| `step2_validate_retail_domain` | 2 | Validate concept / date / location | `gpt-4o-mini` / `gpt-4o` |
| `step3_map_to_ontology` | 3 | Fuzzy index ontology mapping | `gpt-5.2` (disambiguation only) |
| `step4_tlk_lookup` | 4 | TLK template SQL lookup | `o4-mini` |
| `step5_execute_query` | 5 | Execute SQL + summarise results | `gpt-4o-mini` |
| `get_retail_schema` | — | Return DDL schema for a product | — |

---

## Quick Start

**Prerequisites:** [Pixi](https://pixi.sh/latest/#installation) · Python ≥ 3.11 · OpenAI API key

```bash
# 1. Clone
git clone <repo-url> && cd retail-analytics

# 2. Configure environment
cp .env.example .env          # then edit: set OPEN_API_KEY

# 3. Install dependencies
pixi install

# 4a. Run as HTTP MCP server (default port 8080)
pixi run retail-sfc

# 4b. Run in stdio mode (for Claude Desktop / MCP clients)
pixi run python start_stdio.py

# 4c. Explore the pipeline via notebooks (no MCP client needed)
pixi run jupyter lab
#   → notebooks/full_workflow.ipynb        (S1→S2→S3b, from origin/milan)
#   → notebooks/pipeline_full_test_fixed.ipynb   (S1→S2→S3b→S3.25→S3.5→S4→S5, from origin/juanantonio)
```

### Docker

```bash
docker build -t retail-sfc .
docker run -e OPEN_API_KEY=sk-... -p 8080:8080 retail-sfc
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_API_KEY` | — | **Required.** OpenAI API key |
| `BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL (proxy / Azure) |
| `MCP_HOST` | `0.0.0.0` | Host for the HTTP MCP server |
| `MCP_PORT` | `8080` | Port for the HTTP MCP server |

---

## Project Structure

```
retail-analytics/
├── src/retail_electronics/         # Main package
│   ├── llm/                # OpenAI client wrapper
│   ├── ontology/           # Index build, fuzzy search, translations
│   ├── tools/              # One module per pipeline step
│   ├── server.py           # FastMCP server + tool registration
│   └── config.py           # Env vars, paths, per-step model config
├── data/
│   ├── TLK/                # TLK_Library.json — SQL template library
│   ├── ontology/           # Product ontology JSON + dimension CSVs
│   └── retail_analytics.ddl
├── docs/                   # See docs/index.md
├── notebooks/              # Exploration & demo notebooks
├── start_stdio.py          # Stdio transport entry point (MCP clients)
├── Dockerfile              # Pixi-based multi-stage build
└── pyproject.toml          # Dependencies + Pixi workspace config
```

---

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

- [`docs/architecture.md`](docs/architecture.md) — modules, pipeline, data dependencies
- [`docs/ontology.md`](docs/ontology.md) — product hierarchy design and structure
- [`docs/documentation.html`](docs/documentation.html) — interactive full reference
- [`docs/workflow.html`](docs/workflow.html) — visual pipeline diagram
- [`docs/bugs/`](docs/bugs/) — QA session HTML reports
