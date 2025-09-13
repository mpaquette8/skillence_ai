# // file: tests/test_api_lessons.py

"""
Tests d'intégration simplifiés pour les endpoints /v1/lessons.
Utilise la DB principale (skillence_ai.db) avec nettoyage avant chaque test.
Approche pragmatique MVP : moins d'isolation mais plus simple et robuste.
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — alternative: unittest mais moins d'outils
# - httpx (tierce) : client HTTP async pour tests ASGI — nécessaire pour FastAPI  
# - api.main (local) : app FastAPI à tester — point d'entrée principal
# - storage.base (local) : get_session pour vérifier persistance — accès DB
# - storage.models (local) : Request, Lesson pour vérifications — modèles ORM
import pytest
import httpx
from httpx import ASGITransport
from api.main import app
from storage.base import get_session
from storage.models import Request, Lesson


@pytest.fixture(autouse=True)
def clean_db():
    """
    Nettoie la DB avant chaque test.
    Approche simple : supprime toutes les données de test.
    """
    with get_session() as db:
        # Supprimer toutes les leçons et requêtes
        db.query(Lesson).delete()
        db.query(Request).delete()
        db.commit()


@pytest.mark.asyncio
async def test_create_lesson_happy_path():
    """
    Test du cycle complet : POST → génération → persistance → réponse.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "subject": "La photosynthese test", 
            "audience": "lyceen", 
            "duration": "short"
        }
        
        resp = await client.post("/v1/lessons", json=payload)
        
        # Vérifications réponse API
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "lesson_id" in data
        assert len(data["lesson_id"]) == 36  # UUID format
        assert data["title"] == "La photosynthese test (niveau lyceen)"
        assert data["message"] == "Leçon générée avec succès"
        assert data["from_cache"] is False  # Première génération
        
        # Vérifications persistance en base
        with get_session() as db:
            request = db.query(Request).filter(Request.subject == "La photosynthese test").first()
            assert request is not None
            assert request.audience == "lyceen"
            assert request.duration == "short"
            
            lesson = db.query(Lesson).filter(Lesson.id == data["lesson_id"]).first()
            assert lesson is not None
            assert lesson.title == "La photosynthese test (niveau lyceen)"
            assert lesson.content_md.startswith("#")
            assert len(lesson.objectives) >= 2
            assert len(lesson.plan) >= 3
            assert len(lesson.quiz) == 5


@pytest.mark.asyncio 
async def test_get_lesson_by_id():
    """
    Test GET /v1/lessons/{id} après création.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Créer une leçon
        create_payload = {"subject": "Test GET unique", "audience": "adulte", "duration": "medium"}
        create_resp = await client.post("/v1/lessons", json=create_payload)
        assert create_resp.status_code == 200
        lesson_id = create_resp.json()["lesson_id"]
        
        # Récupérer via GET
        get_resp = await client.get(f"/v1/lessons/{lesson_id}")
        assert get_resp.status_code == 200
        
        data = get_resp.json()
        assert data["id"] == lesson_id
        assert data["title"] == "Test GET unique (niveau adulte)"
        assert data["content"].startswith("#")
        assert isinstance(data["objectives"], list)
        assert isinstance(data["plan"], list)
        assert len(data["quiz"]) == 5


@pytest.mark.asyncio
async def test_idempotence():
    """
    Test idempotence : même requête → même résultat.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {"subject": "Test idempotence", "audience": "enfant", "duration": "short"}
        
        # Premier appel
        resp1 = await client.post("/v1/lessons", json=payload)
        assert resp1.status_code == 200
        data1 = resp1.json()
        lesson_id_1 = data1["lesson_id"]
        assert data1["from_cache"] is False
        
        # Deuxième appel identique
        resp2 = await client.post("/v1/lessons", json=payload)
        assert resp2.status_code == 200
        data2 = resp2.json()
        
        # Vérifications idempotence
        assert data2["lesson_id"] == lesson_id_1  # Même ID
        assert data2["from_cache"] is True  # Cache détecté
        
        # Vérifier une seule leçon en base
        with get_session() as db:
            count = db.query(Lesson).filter(Lesson.title.contains("Test idempotence")).count()
            assert count == 1


@pytest.mark.asyncio
async def test_get_nonexistent_lesson():
    """
    Test GET avec un ID inexistant → 404.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = "nonexistent-id-12345"
        resp = await client.get(f"/v1/lessons/{fake_id}")
        
        assert resp.status_code == 404
        assert "non trouvée" in resp.json()["detail"]


@pytest.mark.asyncio  
async def test_invalid_payload_validation():
    """
    Test validation Pydantic : payload invalide → 422.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Payload avec champs manquants
        invalid_payload = {"subject": "Test"}  # Manque audience et duration
        
        resp = await client.post("/v1/lessons", json=invalid_payload)
        
        assert resp.status_code == 422  # Unprocessable Entity
        error_detail = resp.json()["detail"]
        assert len(error_detail) >= 2  # Au moins 2 champs manquants


@pytest.mark.asyncio
async def test_different_requests_different_lessons():
    """
    Test que des requêtes différentes génèrent des leçons différentes.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Requête 1
        payload1 = {"subject": "Sujet A unique", "audience": "lyceen", "duration": "short"}
        resp1 = await client.post("/v1/lessons", json=payload1)
        assert resp1.status_code == 200
        lesson_id_1 = resp1.json()["lesson_id"]
        
        # Requête 2 (différente)
        payload2 = {"subject": "Sujet B unique", "audience": "lyceen", "duration": "short"} 
        resp2 = await client.post("/v1/lessons", json=payload2)
        assert resp2.status_code == 200
        lesson_id_2 = resp2.json()["lesson_id"]
        
        # Vérifications
        assert lesson_id_1 != lesson_id_2  # IDs différents
        
        # Vérifier 2 leçons distinctes en base
        with get_session() as db:
            lessons_a = db.query(Lesson).filter(Lesson.title.contains("Sujet A unique")).count()
            lessons_b = db.query(Lesson).filter(Lesson.title.contains("Sujet B unique")).count()
            assert lessons_a == 1
            assert lessons_b == 1
