"""
app/router/service.py
─────────────────────
Routes a user query to industry + domains using the agent_model.
"""
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.exceptions import RouterError
from app.router.schemas import RouterOutput
from app.services.llm import complete_json

_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "router.md"
_SYSTEM_PROMPT: str = _PROMPT_PATH.read_text(encoding="utf-8")


async def route_query(query: str) -> RouterOutput:
    """
    Classify the query into an industry and list of relevant domains.
    Uses the fast agent_model for speed.
    """
    logger.info(f"Routing query: {query[:80]}...")
    try:
        result = await complete_json(
            system=_SYSTEM_PROMPT,
            user=f"Decision query to classify:\n\n{query}",
            model=settings.agent_model,
            schema=RouterOutput,
            temperature=0.3,  # Low temp for classification accuracy
        )
        logger.info(
            f"Routed → industry={result.industry} domains={result.domains} complexity={result.complexity}"
        )
        return result
    except Exception as exc:
        raise RouterError(f"Routing failed: {exc}", detail={"query": query[:200]}) from exc
