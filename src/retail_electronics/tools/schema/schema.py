"""get_schema tool — read DDL from local file."""

import logging

from retail_electronics.config import DDL_PATH

logger = logging.getLogger(__name__)


def get_schema(product: str) -> str:
    """Return the DDL schema for the given product.

    Args:
        product: The product name. Currently supported: retail_analytics

    Returns:
        DDL string for the given product.
    """
    try:
        ddl_file = DDL_PATH
        if not ddl_file.exists():
            ddl_file = DDL_PATH.parent.parent / f"{product}.ddl"
        return ddl_file.read_text()
    except Exception as e:
        return f"Error getting schema for {product}: {e}"
