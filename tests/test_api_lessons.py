"""
Tests d'intégration CORRIGÉS pour /v1/lessons (SANS QUIZ) - v0.1.2.

CORRECTIF:
- Fixture clean_db sécurisée (gère les tables manquantes)
- Suppression de toutes les vérifications quiz
- Focus sur la qualité du contenu (plan, objectifs, Markdown)
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — alternative: unittest mais moins d'outils
# - httpx (tierce) : client HTTP async pour tests ASGI — nécessaire pour FastAPI  
# - api.main (local) : app FastAPI à tester — point d'entrée principal
# - storage.base (local) : get_session pour vérifier persistance + init_db — accès DB
# - storage.models (local) : Request, Lesson pour vérifications — modèles ORM
import pytest
import httpx
from httpx import ASGITransport
from api.main import app
from storage.base import get_session, init_db
from storage.models import Request, Lesson


@pytest.fixture(autouse=True)
def clean_db():
    """
    Nettoie la DB avant chaque test (SÉCURISÉ).
    Crée les tables si elles n'existent pas.
    """
    # S'assurer que les tables existent
    init_db()
    
    # Nettoyer les données de test
    with get_session() as db:
        try:
            db.query(Lesson).delete()
            db.query(Request).delete()
            db.commit()
        except Exception:
            # Si les tables n'existent pas encore, les créer
            db.rollback()
            init_db()


@pytest.mark.asyncio
async def test_create_lesson_happy_path():
    """
    Test du cycle complet : POST → génération → persistance → réponse.
    FOCUS: contenu de qualité (objectives + plan + markdown).
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "subject": "La photosynthese test", 
            "audience": "lycéen",
            "duration": "short"
        }
        
        resp = await client.post("/v1/lessons", json=payload)
        
        # Vérifications réponse API
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        data = resp.json()
        
        assert "lesson_id" in data
        assert len(data["lesson_id"]) == 36  # UUID format
        assert data["title"] == "La photosynthese test (niveau lycéen)"
        assert data["message"] == "Leçon pédagogique générée avec succès"
        assert data["from_cache"] is False
        
        # Vérifications persistance en base (SANS QUIZ)
        with get_session() as db:
            request = db.query(Request).filter(Request.subject == "La photosynthese test").first()
            assert request is not None
            assert request.audience == "lycéen"
            assert request.duration == "short"
            
            lesson = db.query(Lesson).filter(Lesson.id == data["lesson_id"]).first()
            assert lesson is not None
            assert lesson.title == "La photosynthese test (niveau lycéen)"
            assert lesson.content_md.startswith("#")  # Markdown valide
            assert len(lesson.objectives) >= 1  # Au moins un objectif
            assert len(lesson.plan) >= 2  # Au moins 2 sections


@pytest.mark.asyncio 
async def test_get_lesson_by_id():
    """
    Test GET /v1/lessons/{id} après création (SANS QUIZ).
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
        assert data["content"].startswith("#")  # Markdown
        assert isinstance(data["objectives"], list)
        assert isinstance(data["plan"], list)
        assert len(data["objectives"]) >= 1
        assert len(data["plan"]) >= 2


@pytest.mark.asyncio
async def test_idempotence():
    """
    Test idempotence : même requête → même résultat (SANS QUIZ).
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
async def test_strict_enum_validation():
    """
    Test validation stricte des enum audience/duration.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        # Test audience invalide
        invalid_audience_payload = {
            "subject": "Test enum", 
            "audience": "lyceen",  # Sans accent = invalide
            "duration": "short"
        }
        resp = await client.post("/v1/lessons", json=invalid_audience_payload)
        assert resp.status_code == 422
        error = resp.json()["detail"][0]
        assert "literal_error" in error["type"]
        assert "enfant" in error["msg"] and "lycéen" in error["msg"]
        
        # Test duration invalide
        invalid_duration_payload = {
            "subject": "Test enum",
            "audience": "adulte", 
            "duration": "fast"  # Invalide
        }
        resp = await client.post("/v1/lessons", json=invalid_duration_payload)
        assert resp.status_code == 422
        error = resp.json()["detail"][0]
        assert "literal_error" in error["type"]
        assert "short" in error["msg"] and "medium" in error["msg"]
        
        # Test avec enum valides
        valid_payload = {
            "subject": "Test enum valide",
            "audience": "lycéen", 
            "duration": "medium"
        }
        resp = await client.post("/v1/lessons", json=valid_payload)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_different_requests_different_lessons():
    """
    Test que des requêtes différentes génèrent des leçons différentes.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Requête 1
        payload1 = {"subject": "Sujet A unique", "audience": "lycéen", "duration": "short"}
        resp1 = await client.post("/v1/lessons", json=payload1)
        assert resp1.status_code == 200
        lesson_id_1 = resp1.json()["lesson_id"]
        
        # Requête 2 (différente)
        payload2 = {"subject": "Sujet B unique", "audience": "lycéen", "duration": "short"} 
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


@pytest.mark.asyncio
async def test_all_valid_enum_combinations():
    """
    Test toutes les combinaisons valides d'audience/duration.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        
        valid_combinations = [
            ("enfant", "short"),
            ("enfant", "medium"), 
            ("enfant", "long"),
            ("lycéen", "short"),
            ("lycéen", "medium"),
            ("lycéen", "long"),
            ("adulte", "short"),
            ("adulte", "medium"),
            ("adulte", "long")
        ]
        
        for i, (audience, duration) in enumerate(valid_combinations):
            payload = {
                "subject": f"Test combinaison {i+1}",
                "audience": audience,
                "duration": duration
            }
            resp = await client.post("/v1/lessons", json=payload)
            assert resp.status_code == 200, f"Failed for {audience}/{duration}: {resp.text}"
            
            data = resp.json()
            expected_title = f"Test combinaison {i+1} (niveau {audience})"
            assert data["title"] == expected_title


@pytest.mark.asyncio
async def test_content_quality_validation():
    """
    Test de la qualité du contenu généré (nouveaux critères v0.1.2).
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "subject": "L'évaporation de l'eau", 
            "audience": "enfant", 
            "duration": "medium"
        }
        
        resp = await client.post("/v1/lessons", json=payload)
        assert resp.status_code == 200
        lesson_id = resp.json()["lesson_id"]
        
        # Récupérer le contenu détaillé
        detail_resp = await client.get(f"/v1/lessons/{lesson_id}")
        assert detail_resp.status_code == 200
        
        lesson_data = detail_resp.json()
        
        # Validations qualité contenu
        assert len(lesson_data["content"]) > 200  # Contenu substantiel
        assert "## Objectifs d'apprentissage" in lesson_data["content"]  # Structure
        assert "## Plan de la leçon" in lesson_data["content"]
        assert "## Contenu" in lesson_data["content"]
        
        # Objectifs et plan remplis
        assert len(lesson_data["objectives"]) >= 2
        assert len(lesson_data["plan"]) >= 3
        
        # Titre adapté à l'audience
        assert "enfant" in lesson_data["title"] or "(niveau enfant)" in lesson_data["title"]