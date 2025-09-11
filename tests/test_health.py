# file: tests/test_health.py
import pytest
from httpx import AsyncClient, ASGITransport
from api.main import app

@pytest.mark.asyncio
async def test_health():
    """
    Test du endpoint /v1/health.
    Vérifie que la réponse est 200 et que le JSON est {"status": "ok"}.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}