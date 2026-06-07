"""
tests/unit/test_health.py
─────────────────────────
Phase 0 exit criteria: app starts, DB is reachable, health endpoint returns ok.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_returns_ok(client: AsyncClient) -> None:
    """GET /api/v1/health → 200 with status=ok and database=connected."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["app"] == "Delphi"


@pytest.mark.asyncio
async def test_health_check_contains_version(client: AsyncClient) -> None:
    """Health response includes app version."""
    response = await client.get("/api/v1/health")
    data = response.json()
    assert "version" in data
    assert len(data["version"]) > 0


@pytest.mark.asyncio
async def test_docs_available_in_dev(client: AsyncClient) -> None:
    """OpenAPI docs should be accessible in development mode."""
    response = await client.get("/docs")
    assert response.status_code == 200
