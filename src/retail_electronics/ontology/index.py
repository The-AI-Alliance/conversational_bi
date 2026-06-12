"""Build in-memory search index from ontology JSON + dimension CSVs."""

from __future__ import annotations

import csv
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from retail_electronics.config import (
    DIM_FAMILY_CSV,
    DIM_PRODUCT_TYPE_CSV,
    DIM_SUBFAMILY_CSV,
    ONTOLOGY_JSON_PATH,
)

logger = logging.getLogger(__name__)


@dataclass
class ItemMatch:
    """A direct item match from the master_articles DB (DuckDB fallback)."""

    item_code: str
    item_name: str


@dataclass
class IndexNode:
    """A single searchable node in the product hierarchy."""

    path: str  # "AUDIO/Headphones/Over-Ear Wireless Headphones"
    family: str
    subfamily: str | None = None
    product_category: str | None = None
    product_type: str | None = None
    level: int = 1  # 1=family, 2=subfamily, 3=product_category, 4=product_type
    sku_count: int = 0
    sample_items: list[str] = field(default_factory=list)


class OntologyIndex:
    """Lightweight in-memory index of ~3,315 product hierarchy nodes."""

    def __init__(self) -> None:
        self.nodes: list[IndexNode] = []
        self.name_to_paths: dict[str, list[str]] = {}
        self._built = False

    def build(self, ontology_path: Path | None = None) -> None:
        """Parse ontology JSON and build the flat index."""
        ontology_path = ontology_path or ONTOLOGY_JSON_PATH

        if not ontology_path.exists():
            logger.warning(
                "Ontology JSON not found at %s — trying CSVs", ontology_path
            )
            self._build_from_csvs()
            return

        with open(ontology_path) as f:
            data = json.load(f)

        children = data.get("children", {})
        for family_name, family_data in children.items():
            family_node = IndexNode(
                path=family_name,
                family=family_name,
                level=1,
                sku_count=family_data.get("sku_count", 0),
            )
            self._add_node(family_node)

            for sub_name, sub_data in family_data.get("children", {}).items():
                sub_path = f"{family_name}/{sub_name}"
                sub_node = IndexNode(
                    path=sub_path,
                    family=family_name,
                    subfamily=sub_name,
                    level=2,
                    sku_count=sub_data.get("sku_count", 0),
                )
                self._add_node(sub_node)

                for cat_name, cat_data in sub_data.get("children", {}).items():
                    cat_path = f"{family_name}/{sub_name}/{cat_name}"
                    cat_node = IndexNode(
                        path=cat_path,
                        family=family_name,
                        subfamily=sub_name,
                        product_category=cat_name,
                        level=3,
                        sku_count=cat_data.get("sku_count", 0),
                    )
                    self._add_node(cat_node)

                    for pt_name, pt_data in cat_data.get(
                        "children", {}
                    ).items():
                        pt_path = (
                            f"{family_name}/{sub_name}/{cat_name}/{pt_name}"
                        )
                        samples = pt_data.get("sample_items", [])
                        pt_node = IndexNode(
                            path=pt_path,
                            family=family_name,
                            subfamily=sub_name,
                            product_category=cat_name,
                            product_type=pt_name,
                            level=4,
                            sku_count=pt_data.get("sku_count", 0),
                            sample_items=samples,
                        )
                        self._add_node(pt_node)

        self._built = True
        logger.info(
            "Ontology index built: %d nodes (%d families)",
            len(self.nodes),
            sum(1 for n in self.nodes if n.level == 1),
        )

    def _build_from_csvs(self) -> None:
        """Fallback: build index from dimension CSV files."""
        family_map: dict[str, str] = {}  # family_id -> name
        sub_family_map: dict[str, tuple[str, str]] = {}  # sub_id -> (family_id, name)

        if DIM_FAMILY_CSV.exists():
            with open(DIM_FAMILY_CSV) as f:
                for row in csv.DictReader(f):
                    fid = row["family_id"]
                    fname = row["family_name"]
                    family_map[fid] = fname
                    node = IndexNode(
                        path=fname, family=fname, level=1,
                    )
                    self._add_node(node)

        if DIM_SUBFAMILY_CSV.exists():
            with open(DIM_SUBFAMILY_CSV) as f:
                for row in csv.DictReader(f):
                    sid = row["subfamily_id"]
                    fid = row["family_id"]
                    sname = row["subfamily_name"]
                    fname = family_map.get(fid, "UNKNOWN")
                    sub_family_map[sid] = (fid, sname)
                    path = f"{fname}/{sname}"
                    node = IndexNode(
                        path=path, family=fname, subfamily=sname, level=2,
                    )
                    self._add_node(node)

        if DIM_PRODUCT_TYPE_CSV.exists():
            with open(DIM_PRODUCT_TYPE_CSV) as f:
                for row in csv.DictReader(f):
                    sid = row["subfamily_id"]
                    pt_name = row["product_type_name"]
                    fid, sname = sub_family_map.get(sid, ("", ""))
                    fname = family_map.get(fid, "UNKNOWN")
                    path = f"{fname}/{sname}/{pt_name}"
                    node = IndexNode(
                        path=path, family=fname, subfamily=sname,
                        product_type=pt_name, level=3,
                    )
                    self._add_node(node)

        self._built = True
        logger.info(
            "Ontology index built from CSVs: %d nodes", len(self.nodes)
        )

    def _add_node(self, node: IndexNode) -> None:
        self.nodes.append(node)
        name = (
            node.product_type
            or node.product_category
            or node.subfamily
            or node.family
        )
        name_lower = name.lower()
        self.name_to_paths.setdefault(name_lower, []).append(node.path)

    def get_node_by_path(self, path: str) -> IndexNode | None:
        for node in self.nodes:
            if node.path == path:
                return node
        return None

    @property
    def families(self) -> list[IndexNode]:
        return [n for n in self.nodes if n.level == 1]

    @property
    def is_built(self) -> bool:
        return self._built


# Module-level singleton
_index: OntologyIndex | None = None


def get_index() -> OntologyIndex:
    """Get or build the singleton ontology index."""
    global _index
    if _index is None or not _index.is_built:
        _index = OntologyIndex()
        _index.build()
    return _index
