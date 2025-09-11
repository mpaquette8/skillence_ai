import pytest
from httpx import AsyncClient
from api.main import app

@pytest.mark.asyncio
async def test_health():
    """
    Test du endpoint /v1/health.
    Vérifie que la réponse est 200 et que le JSON est {"status": "ok"}.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
