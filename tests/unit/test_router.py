"""
tests/unit/test_router.py
──────────────────────────
Unit tests for the Query Router (mocked LLM).
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.router.schemas import RouterOutput
from app.router.service import route_query


MOCK_ROUTER_OUTPUT = RouterOutput(
    industry="healthcare",
    domains=["legal", "security", "technical", "finance"],
    complexity="high",
    reasoning="Hospital AI deployment touches patient safety, regulatory, and technical domains.",
)


@pytest.mark.asyncio
async def test_route_query_returns_router_output():
    """Router returns a valid RouterOutput with expected fields."""
    with patch("app.router.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_ROUTER_OUTPUT
        result = await route_query("Should we deploy AI diagnostics in our ER?")

    assert isinstance(result, RouterOutput)
    assert result.industry == "healthcare"
    assert "legal" in result.domains
    assert result.complexity in ("low", "medium", "high")


@pytest.mark.asyncio
async def test_route_query_uses_agent_model():
    """Router should use the fast agent_model, not judge_model."""
    from app.core.config import settings

    with patch("app.router.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_ROUTER_OUTPUT
        await route_query("Market expansion into Southeast Asia?")

    call_kwargs = mock_llm.call_args.kwargs
    assert call_kwargs["model"] == settings.agent_model


@pytest.mark.asyncio
async def test_route_query_includes_at_least_two_domains():
    """Router output must include at least 2 domains per spec."""
    with patch("app.router.service.complete_json", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = MOCK_ROUTER_OUTPUT
        result = await route_query("Cybersecurity investment decision?")

    assert len(result.domains) >= 2
