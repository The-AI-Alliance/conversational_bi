"""Configuration: environment variables, paths, constants, model configs."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
TLK_LIBRARY_PATH = DATA_DIR / "TLK" / "TLK_Library.json"
DDL_PATH = DATA_DIR / "retail_analytics.ddl"
PARQUET_DIR = DATA_DIR / "parquets"
ONTOLOGY_JSON_PATH = DATA_DIR / "ontology" / "ontology_product.json"
ONTOLOGY_FINAL_JSON_PATH = DATA_DIR / "ontology" / "ontology_product_final.json"
SYNONYMS_PATH = DATA_DIR / "ontology" / "synonyms.json"
DIM_FAMILY_CSV = DATA_DIR / "ontology" / "dim_product_family.csv"
DIM_SUBFAMILY_CSV = DATA_DIR / "ontology" / "dim_product_subfamily.csv"
DIM_PRODUCT_TYPE_CSV = DATA_DIR / "ontology" / "dim_product_type.csv"

# ── OpenAI ───────────────────────────────────────────────────────────
OPENAI_API_KEY = os.environ.get("OPEN_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("BASE_URL", "https://api.openai.com/v1")

# ── Ollama (local — Step 3.5 SKU filter) ─────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
MODEL_SKU_FILTER = os.environ.get("MODEL_SKU_FILTER", "gpt-5.1")

# Per-step model selection
MODEL_CLASSIFY = os.environ.get("MODEL_CLASSIFY", "gpt-4o-mini")
MODEL_VALIDATE = os.environ.get("MODEL_VALIDATE", "gpt-4o-mini")
MODEL_VALIDATE_CONCEPT = os.environ.get("MODEL_VALIDATE_CONCEPT", "gpt-4o")
MODEL_ONTOLOGY = os.environ.get("MODEL_ONTOLOGY", "gpt-5.1")
MODEL_TLK = os.environ.get("MODEL_TLK", "o4-mini")
MODEL_SUMMARIZE = os.environ.get("MODEL_SUMMARIZE", "gpt-4o-mini")


# ── MCP Server ───────────────────────────────────────────────────────
MCP_HOST = os.environ.get("MCP_HOST", "0.0.0.0")
MCP_PORT = int(os.environ.get("MCP_PORT", 8080))

# ── Thresholds ───────────────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = 0.6
