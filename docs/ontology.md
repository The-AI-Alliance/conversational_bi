# Retail Product Ontology

## Why an Ontology?

A football club retail operation like Sevilla FC sells everything from official match kits to keychains, jewelry, and home decoration items. The SAP master data contains ~29,000 SKUs with inconsistent naming conventions spanning over a decade of seasons. Without a structured taxonomy, it is impossible to:

- Ask analytical questions like "how did Textile-Competition revenue evolve across seasons?"
- Feed an LLM with a compact, interpretable product hierarchy for natural-language queries
- Build dimension tables for a data warehouse (Athena/Redshift)

The ontology solves this by creating a **three-level product hierarchy** (Family > Subfamily > Product Type) plus orthogonal temporal and organizational dimensions, all derived from the actual transaction data.

---

## Design Principles

### 1. Only What Sells Matters

The SAP master table (`oitm`) contains 29,358 SKUs, but many are historical artifacts, test entries, or items marked "(NO USAR)" (do not use). The first design decision is to **filter down to items that actually appear in transactions** (`inv1`, 3.5M+ records). This reduces the universe to 22,413 SKUs — a 23.7% reduction that eliminates noise from the taxonomy.

### 2. Trust Authoritative Sources First

Product classification follows a strict priority chain:

| Priority | Source | Coverage | Description |
|----------|--------|----------|-------------|
| 1 | `sei_models` reference table | 97.3% (21,807 SKUs) | Official family/subfamily from the SEI merchandising system |
| 2 | Keyword pattern matching | 0.9% (193 SKUs) | 80+ regex rules applied to parsed product names |
| 3 | Fallback to "OTROS" | 3.2% (724 SKUs) | Catch-all for edge cases (beverages, promo items, sponsorships) |

This three-tier strategy maximizes accuracy: the vast majority of items get their classification from the authoritative `sei_models` join, keyword rules cover the gap for items with clear names but no SEI match, and only a small tail ends up unclassified.

### 3. Extract Structure from Unstructured Names

SAP item names follow at least four different naming conventions accumulated over the years:

```
"24/25 - TF7496 PANTALON PASEO SFC CAVIAR/TOMATO (3-M)"
"150254/100 Cortaviento SAT 12/13 SFC Rojo (6-XXL)"
"SP0246 - Sudadera Cap Ent SFC 18/19 Rojo"
"Camiseta 1ª SFC 22/23 Ad Inf"
```

A regex pipeline parses each format to extract the **product type** (e.g., "PANTALON PASEO", "Cortaviento", "Sudadera Cap Ent") with a 100% parse success rate. This parsed type is the leaf node of the hierarchy.

### 4. Preserve Metadata at the Leaf Level

Each product type node stores rich metadata:

- **SKU count** — how many variants exist
- **Colors** — top 20 color values found
- **Sizes** — top 20 size values
- **Target ages** — Adulto, Junior, Nino, Bebe
- **Seasons** — which seasons the product appeared in
- **Sample items** — 3 example product names for human verification

This metadata makes the ontology self-documenting: anyone inspecting a node can immediately understand what it represents.

---

## The Product Hierarchy

```
Sevilla FC Retail (root)
├── TEXTIL (16,370 SKUs) ........... Apparel: kits, training wear, casual clothing
│   ├── Competicion (1,688) ........ Match-day kits, official jerseys
│   ├── Entrenamiento (2,216) ...... Training gear, warm-ups, technical wear
│   ├── Paseo (3,105) .............. Leisurewear, polos, jackets
│   ├── Casual (592) ............... Everyday fashion items
│   ├── RopaInterior (237) ......... Underwear, socks, base layers
│   └── General (8,532) ............ Unspecified textile items
├── CALZADO (2,914) ................ Footwear: boots, sneakers, sandals
├── COMPLEMENTO (1,306) ............ Accessories: scarves, caps, gloves, bags
├── BAZAR (347) .................... Novelty & gift items
├── ESTADIO (227) .................. Stadium-specific merchandise
├── JOYERIA (220) .................. Jewelry: rings, bracelets, pendants
├── MARROQUINERIA (214) ............ Leather goods: wallets, belts
├── HOGAR (51) ..................... Home items: mugs, blankets, cushions
├── SERIGRAFIA (40) ................ Printing/customization services
└── OTROS (724) .................... Catch-all: promo items, beverages, misc
```

**Why these ten families?** They come directly from the `u_seifam` field in the SEI merchandising system, which Sevilla FC's retail team already uses operationally. The ontology respects the existing business vocabulary rather than inventing a new one.

**Why "General" subfamilies?** When the SEI source provides a family but no specific subfamily, items land in "General". This is intentional — it's better to classify at the family level than to guess the subfamily. The 8,532 "General" items under TEXTIL represent a future enrichment opportunity.

---

## Temporal Dimension

Retail for a football club is inherently seasonal. The ontology includes a fiscal calendar hierarchy:

```
Season (e.g., "24/25")
├── Semester 1 (Jul-Dec) / Semester 2 (Jan-Jun)
│   ├── Quarter (Q1-Q4)
│   │   └── Month
```

14 seasons are covered (12/13 through 25/26), each aligned to the football calendar (July start). This enables season-over-season comparisons and trend analysis.

---

## Organizational Dimension

Derived from the cost centers table (`cecos`), this hierarchy maps the business structure:

```
Area (e.g., "06-NEGOCIOS")
├── Department (e.g., "Tiendas")
│   └── Cost Center (51 total)
```

This allows filtering transactions by organizational unit — distinguishing stadium shop sales from online, wholesale from retail, etc.

---

## Output Formats

The notebook generates multiple output formats for different consumers:

| File | Format | Size | Use Case |
|------|--------|------|----------|
| `ontology_product.json` | Nested JSON | 2.1 MB | LLM context injection, API responses |
| `ontology_product.yaml` | YAML | 1.5 MB | Human review, configuration |
| `ontology_full.json` | Nested JSON | 2.4 MB | Complete (product + temporal + org) |
| `ontology_ddl.sql` | SQL DDL | — | Athena/warehouse table creation |
| `dim_*.csv` / `bridge_*.csv` | CSV | — | Warehouse dimension loading |

### Dimension Tables (Star Schema)

```
dim_product_family (10 rows)
dim_product_subfamily (21 rows)
dim_product_type (3,284 rows)
bridge_sku_taxonomy (22,413 rows)  ──→  links SKUs to their type/subfamily/family
dim_temporal (14 rows)
dim_organization (51 rows)
```

The bridge table pattern allows a single SKU to be queried at any level of the hierarchy without denormalization.

---

## Interactive Visualization

Running `pixi run ontology` starts an HTTP server at `http://localhost:8888` that serves a D3.js tree visualization:

- **Color-coded families** — each family has a distinct color for quick identification
- **Proportional node sizes** — nodes scale with SKU count
- **Tooltips** — hover to see metadata (colors, sizes, ages, seasons, samples)
- **Search** — find and auto-expand nodes matching a keyword
- **Expand/Collapse** — explore the tree interactively

The visualization is generated by `ontology/build_tree.py` from the JSON output.

---

## How to Run

```bash
# Step 1: Build the ontology (run the notebook end-to-end)
#         This reads source parquet files and generates all outputs in data/
pixi run jupyter lab
# Then execute notebooks/ontology_analysis.ipynb

# Step 2: Serve the interactive visualization
pixi run ontology          # builds HTML + starts server at :8888

# Or just build the HTML without serving
pixi run ontology-build
```

---

## Quality Notes & Known Limitations

- **48.9% of items lack a canonical product type** — they have a family and subfamily from SEI but the regex parser could not determine a specific type from the item name. These are classified at the subfamily level and flagged `needs_review`.
- **"OTROS" catch-all (724 items, 3.2%)** contains genuinely miscellaneous items: beverages, promotional giveaways, livestock-related entries, and TV sponsorship line items that exist in the SAP system.
- **Season parsing is approximate** — older items use inconsistent season codes (`t15-16` vs `T20/21` vs `ST`). The temporal dimension relies on the fiscal calendar rather than item-level season tags.
- **The keyword rules are Sevilla FC-specific** — the 80+ regex patterns reference Spanish product terminology and SFC naming conventions. Adapting to another club would require rewriting the classification rules.
