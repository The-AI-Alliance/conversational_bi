# Retail Product Ontology

## Why an Ontology?

An electronics retailer's catalogue spans everything from laptops to smart-home sensors, each with its own naming conventions, specs, and variants. A flat SKU list makes it hard to:

- Ask analytical questions like "how did Audio revenue evolve last quarter?"
- Feed an LLM with a compact, interpretable product hierarchy for natural-language queries
- Validate that a question's product concept actually exists in the catalogue before generating SQL

The ontology solves this by creating a **three-level product hierarchy** (Family → Subfamily → Product Type), used by Step 2 (concept validation) and Step 3 (ontology mapping) of the pipeline.

---

## The Product Hierarchy

```
Generated Electronics Retail Ontology (root)
├── COMPUTING ............. Laptops, desktops, monitors, peripherals
├── MOBILE ................ Smartphones, mobile accessories, phone cases, power banks
├── AUDIO .................. Headphones, speakers, soundbars
├── TV & VIDEO ............. Televisions, streaming devices, projectors
├── GAMING ................. Consoles, controllers, gaming accessories
├── SMART HOME ............. Smart speakers, sensors, smart plugs, hubs
└── ACCESSORIES ............ Cables, chargers, adapters, cases
```

- **7 families** → **29 subfamilies** → **95 product types**
- Each product type leaf stores `sku_count` and a handful of `sample_items` (real product names), making the ontology self-documenting for both humans and the LLM.

Example leaf node under `MOBILE → Smartphones`:

```json
{
  "name": "Smartphone 6.7\" Pro",
  "level": 3,
  "sku_count": 3,
  "sample_items": [
    "Smartphone 6.7\" Pro 256GB BLACK",
    "Smartphone 6.7\" Pro 512GB TITANIUM"
  ]
}
```

---

## Supporting Files

| File | Purpose |
|------|---------|
| `ontology_product.json` | Main 3-level hierarchy, used by Step 3 ontology mapping |
| `ontology_product_final.json` | Refined hierarchy variant used by Step 3 (`map.py`) and Step 3.5 (`filter_llm.py`) |
| `ontology_synonyms.json` | Synonym dictionary used by Step 2 to validate that a question's concept exists |
| `synonyms.json` | Synonym lookup used by `search3.py` for concept existence checks |
| `ontology_metrics.json` | Defines the metrics the system understands (e.g. `billing`, `items_sold`) — each with aliases, measure type, and whether it supports forecasting |

`ontology_metrics.json` is what lets Step 2 recognize that "revenue", "sales", and "facturación" all map to the same `billing` metric.

---

## How It's Used in the Pipeline

1. **Step 2 (Validate)** checks the question's product concept against the synonym dictionaries — does this product family/type exist in the catalogue?
2. **Step 3 (Ontology Map)** matches the validated concept to one or more nodes in `ontology_product.json` / `ontology_product_final.json`, returning the matched family/subfamily/product-type path.
3. **Step 3.5 (LLM SKU Filter)** uses the matched nodes' `sample_items` to narrow down to the actual SKUs relevant to the question.

---

## Known Limitations

- The dataset shipped in this repo is a **sample dataset** (271 SKUs across the 95 product types) for demonstration purposes, not a full production catalogue.
- Synonym coverage is English/Spanish-biased; extending to other languages requires adding entries to `ontology_synonyms.json` / `synonyms.json`.
