# conversational_bi — Retail Electronics

> An MCP server that answers natural-language questions about retail operations through a 5-step validation and query pipeline.
> Part of the [AI Alliance: Conversational BI](https://the-ai-alliance.github.io/conversational_bi/) reference architecture.

---

## Overview

The server receives a retail question in plain language, classifies and validates it, maps the product concept to the internal ontology, looks up or generates the SQL query from a template library (TLK), and executes it against Parquet data via DuckDB — returning results with a confidence badge (`ACCURATE`, `MEDIUM`, `LOW`, or `BLOCKED`).

Built with [FastMCP](https://github.com/jlowin/fastmcp), OpenAI models, and managed with [Pixi](https://pixi.sh).

---

## 5-Step Pipeline

```
Question
  │
  ▼
Step 1 · Classify      — electronics_retail | electronics_non_retail | general
  │
  ▼ (electronics_retail only)
Step 2 · Validate      — concept / metric / date / location / size dimensions
  │
  ▼
Step 3 · Ontology Map  — two-pass LLM mapping (subfamily → product type), synonym fallback
  │
  ▼
Step 3.25/3.5 · SKU Prefilter + Filter — deterministic date filter, then LLM-refined SKU selection
  │
  ▼
Step 4 · TLK Lookup    — ACCURATE (template match) / MEDIUM (adapt) / LOW (generate)
  │
  ▼
Step 5 · Execute       — DuckDB query + LLM natural-language summary
```

See [`docs/architecture.md`](docs/architecture.md) for full detail.

---

## MCP Tools

| Tool | Step(s) | Description | Model |
|------|------|-------------|-------|
| `step1_classify_question` | 1 | Classify question scope | `gpt-4o-mini` |
| `step2_validate_retail_domain` | 2 | Validate concept / metric / date / location / size | `gpt-4o-mini` / `gpt-4o` |
| `step3_to_4_pipeline` | 3, 3.25, 3.5, 4 | Ontology mapping → date prefilter → SKU filter → TLK lookup → SQL | `gpt-5.1` / `o4-mini` |
| `step5_execute_query` | 5 | Execute SQL + summarise results | `gpt-4o-mini` |
| `get_retail_schema` | — | Return DDL schema for a product | — |

Steps 3 through 4 are grouped into a single tool to avoid client-side timeouts on multi-call MCP clients.

---

## Installation

### Prerequisites

- Git
- An **OpenAI API key**
- One of the environment setups below

---

### Option 1 — WSL + Pixi (Recommended)

This is the recommended setup. [Pixi](https://pixi.sh) handles the Python environment and all dependencies without needing to manage virtualenvs manually.

**1. Install Pixi** (if you haven't already):

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

Restart your WSL terminal after installation so the `pixi` command is available.

**2. Clone the repository:**

```bash
git clone https://github.com/The-AI-Alliance/conversational_bi.git
cd conversational_bi
```

**3. Set up your environment variables:**

```bash
cp .env.example .env
```

Open `.env` and fill in your OpenAI API key (and any other variables you want to override — see [Environment Variables](#environment-variables) below):

```
OPEN_API_KEY=sk-...
```

**4. Install dependencies:**

```bash
pixi install
```

**5. Run the server:**

```bash
# HTTP MCP server (default port 8080)
pixi run retail-electronics

# stdio mode (for Claude Desktop or other MCP clients)
pixi run python start_stdio.py
```

---

### Option 2 — macOS + Pixi

The workflow on macOS is essentially the same as WSL. Pixi is cross-platform and handles everything.

**1. Install Pixi:**

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

Restart your terminal (or run `source ~/.zshrc` / `source ~/.bash_profile`) so the `pixi` command is available.

**2. Clone and configure:**

```bash
git clone https://github.com/The-AI-Alliance/conversational_bi.git
cd conversational_bi
cp .env.example .env
# Edit .env — at minimum set OPEN_API_KEY
```

**3. Install and run:**

```bash
pixi install
pixi run retail-electronics
```

> **Note:** The current `pyproject.toml` declares `linux-64` as the only Pixi platform, so `pixi install` on macOS will fail unless you add `osx-arm64` or `osx-64` to the `platforms` list in `pyproject.toml` first:
> ```toml
> [tool.pixi.workspace]
> platforms = ["linux-64", "osx-arm64"]  # add your platform here
> ```

---

### Option 3 — Docker

If you prefer a containerised setup and don't want to install Pixi locally:

```bash
docker build -t conversational-bi .
docker run -e OPEN_API_KEY=sk-... -p 8080:8080 conversational-bi
```

The server will be available at `http://localhost:8080`.

---

### Option 4 — Plain Python (venv)

If you can't use Pixi, you can set up a standard virtual environment. Requires **Python ≥ 3.11**.

```bash
git clone https://github.com/The-AI-Alliance/conversational_bi.git
cd conversational_bi

python -m venv .venv
source .venv/bin/activate        # WSL / macOS / Linux
# On Windows CMD: .venv\Scripts\activate

pip install -e .

cp .env.example .env
# Edit .env and set OPEN_API_KEY

python -m retail_electronics     # HTTP server
# or
python start_stdio.py            # stdio mode
```

---

## Connecting to Claude Desktop

Once the server is running in **stdio mode**, add it to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "conversational-bi": {
      "command": "/absolute/path/to/conversational_bi/start_stdio.sh"
    }
  }
}
```

The `start_stdio.sh` script sets the correct `PYTHONPATH` and invokes `start_stdio.py` via the Pixi-managed Python interpreter.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. Only `OPEN_API_KEY` is required — all others have sensible defaults.

| Variable | Default | Description |
|----------|---------|-------------|
| `OPEN_API_KEY` | *(required)* | OpenAI API key |
| `BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible base URL (proxy / Azure) |
| `MCP_HOST` | `0.0.0.0` | Host for the HTTP MCP server |
| `MCP_PORT` | `8080` | Port for the HTTP MCP server |
| `MODEL_CLASSIFY` | `gpt-4o-mini` | Model used in Step 1 |
| `MODEL_VALIDATE` | `gpt-4o-mini` | Model used in Step 2 |
| `MODEL_VALIDATE_CONCEPT` | `gpt-4o` | Model used in Step 2 concept validation |
| `MODEL_ONTOLOGY` | `gpt-5.1` | Model used in Step 3 |
| `MODEL_TLK` | `o4-mini` | Model used in Step 4 |
| `MODEL_SUMMARIZE` | `gpt-4o-mini` | Model used in Step 5 |
| `MODEL_SKU_FILTER` | `gpt-5.1` | Model used in Step 3.5 SKU filter |
| `OLLAMA_BASE_URL` | `http://localhost:11434/v1` | Ollama endpoint (Step 3.5 SKU filter, if using local models) |

---

## Project Structure

```
conversational_bi/
├── src/retail_electronics/         # Main package
│   ├── llm/                        # OpenAI client wrapper
│   ├── ontology/                   # Index build + synonym-based existence search
│   ├── tools/                      # One subpackage per pipeline step
│   ├── server.py                   # FastMCP server + tool registration
│   └── config.py                   # Env vars, paths, per-step model config
├── data/
│   ├── TLK/                        # TLK_Library.json — SQL template library
│   ├── ontology/                   # Product ontology JSON + synonym dictionaries
│   ├── parquets/                   # Data files queried by DuckDB
│   └── retail_analytics.ddl        # Athena-style schema DDL
├── docs/                           # See docs/index.md
├── start_stdio.py                  # stdio transport entry point
├── start_stdio.sh                  # Shell wrapper for Claude Desktop
├── .env.example                    # Environment variable template
├── Dockerfile
└── pyproject.toml                  # Dependencies + Pixi workspace config
```

---

## Documentation

Full documentation lives in [`docs/`](docs/index.md):

- [`docs/architecture.md`](docs/architecture.md) — modules, pipeline, data dependencies
- [`docs/ontology.md`](docs/ontology.md) — product hierarchy design and structure
- [`docs/essay_post.html`](docs/essay_post.html) — AI Alliance companion essay (open in browser)
- [`docs/technical_post.html`](docs/technical_post.html) — AI Alliance technical post (open in browser)
