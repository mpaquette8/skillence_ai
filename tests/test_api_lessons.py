# // file: tests/test_api_lessons.py

"""
Test e2e du POST /v1/lessons (happy path).
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — alternative: unittest (stdlib)
# - httpx (tierce) : client HTTP pour tests ASGI — recommandé avec FastAPI
# - fastapi (tierce) : import app pour le test
# - skillence_ai.api.main (local) : app FastAPI à tester
import pytest  # tierce — runner de tests
from httpx import AsyncClient  # tierce — client HTTP async compatible ASGI
from api.main import app  # local — l'application à tester


@pytest.mark.anyio
async def test_create_lesson_happy_path() -> None:
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {"subject": "La photosynthèse", "audience": "lycéen", "duration": "short"}
        resp = await client.post("/v1/lessons", json=payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["title"].startswith("La photosynthèse")
        assert isinstance(data["plan"], list) and len(data["plan"]) >= 3
        assert "vulgarisée" in data["content"]
