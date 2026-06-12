"""Step 1: classify_question — determine if question is about electronics retail."""

import logging

from retail_electronics.config import MODEL_CLASSIFY
from retail_electronics.llm.client import chat_json
from retail_electronics.tools.display.display import display_s1

logger = logging.getLogger(__name__)

_SYSTEM = """You are a question classifier for an electronics retailer's analytics system.

Classify each question into one of three categories:
- "electronics_retail": Questions requesting retail **data, analytics, or metrics** about electronics merchandise — sales numbers, billing, inventory counts, stock levels, revenue, etc. The question must ask for data, not a definition or explanation.
- "electronics_non_retail": Questions about the electronics retailer but NOT about retail data (store locations, return policies, company info, opening hours, etc.)
- "general": Questions asking for **definitions, explanations, or general knowledge** — even if the subject is an electronics product. Also includes topics unrelated to the electronics retailer entirely.

Disambiguation examples:
- "What is a laptop?" → general (definitional, not a data query)
- "How many laptops sold?" → electronics_retail (data query)
- "What is Bluetooth?" → general (definitional)
- "How many Bluetooth headphones have we sold?" → electronics_retail (data query)
- "Qué es un smartphone?" → general (definitional, even though smartphone is in the catalog)
- "Cuántos smartphones se han vendido?" → electronics_retail (data query)

Respond in JSON with:
{
  "classification": "electronics_retail" | "electronics_non_retail" | "general",
  "reasoning": "brief explanation of why this classification",
  "answer": null or "direct answer string if classification is NOT electronics_retail"
}

If the question is "general" or "electronics_non_retail", provide a brief helpful answer in the "answer" field along with a note that this system specializes in electronics retail analytics.
If the question is "electronics_retail", set answer to null — it will be handled by the pipeline."""


def classify_question(question: str) -> dict:
    """Classify whether a question is about electronics retail, electronics non-retail, or general.

    Args:
        question: The user's question.

    Returns:
        dict with classification, reasoning, and optional answer.
    """
    logger.info("=" * 60)
    logger.info("STEP 1: CLASSIFY QUESTION")
    logger.info("Question: %s", question)

    result = chat_json(
        f"Classify this question:\n\n{question}",
        model=MODEL_CLASSIFY,
        system=_SYSTEM,
    )

    # Ensure required fields
    result.setdefault("classification", "general")
    result.setdefault("reasoning", "")
    result.setdefault("answer", None)

    logger.info("Classification: %s", result["classification"])
    logger.info("Reasoning: %s", result["reasoning"])

    result['display'] = display_s1(result)
    return result
