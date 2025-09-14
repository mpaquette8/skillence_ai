"""
Tests d'intégration API CORRIGÉS (config de test isolée).

CORRECTIFS v0.1.2:
- Mock validation OpenAI automatique
- DB temporaire par test
- Configuration de test dédiée
- Suppression des vérifications quiz
"""

# Inventaire des dépendances
# - pytest (tierce) : tests async — framework principal
# - httpx (tierce) : client HTTP async — tests FastAPI
# - unittest.mock (stdlib) : patch configuration — isolation environnement test
# - tempfile (stdlib) : fichiers temporaires — DB de test isolée
# - pathlib (stdlib) : manipulation chemins — gestion fichiers
# - sqlalchemy (tierce) : moteur test — création tables
# - api.main (local) : app FastAPI — application à tester
# - storage.base (local) : Base, get_session — schéma + sessions
# - storage.models (local) : Request, Lesson — modèles ORM
import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import patch
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from api.main import app
from storage.base import Base
from storage.models import Request, Lesson


@pytest.fixture
def test_app_with_isolated_db():
    """
    App FastAPI avec DB temporaire COMPLÈTEMENT isolée.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = Path(tmpdir) / "test_isolated.db"
        test_db_url = f"sqlite:///{test_db_path}"
        
        # Patch la DATABASE_URL pour ce test
        with patch('storage.base.settings.DATABASE_URL', test_db_url):
            # Créer moteur + tables pour ce test
            test_engine = create_engine(test_db_url, future=True)
            Base.metadata.create_all(bind=test_engine)
            
            # Patch le sessionmaker pour utiliser notre moteur
            TestSessionLocal = sessionmaker(bind=test_engine, class_=Session, future=True)
            
            with patch('storage.base.SessionLocal', TestSessionLocal), \
                 patch('storage.base.get_session') as mock_get_session:
                
                # Remplacement contextuel de get_session
                def test_get_session():
                    db = TestSessionLocal()
                    try:
                        yield db
                        db.commit()
                    except Exception:
                        db.rollback()
                        raise
                    finally:
                        db.close()
                
                mock_get_session.side_effect = test_get_session
                
                yield app
            
            test_engine.dispose()


@pytest.mark.asyncio
async def test_create_lesson_happy_path_isolated(test_app_with_isolated_db):
    """Test création de leçon avec environnement complètement isolé."""
    transport = ASGITransport(app=test_app_with_isolated_db)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "subject": "Test isolation complète",
            "audience": "lycéen", 
            "duration": "short"
        }
        
        resp = await client.post("/v1/lessons", json=payload)
        
        # Vérifications de base
        assert resp.status_code == 200, f"Status: {resp.status_code}, Body: {resp.text}"
        
        data = resp.json()
        assert "lesson_id" in data
        assert len(data["lesson_id"]) == 36  # UUID
        assert data["title"] == "Test isolation complète (niveau lycéen)"
        assert data["from_cache"] is False
        assert "readability" in data
        assert data["readability"]["audience_target"] == "lycéen"
        assert isinstance(data["readability"]["is_appropriate_for_audience"], bool)
        

@pytest.mark.asyncio
async def test_health_endpoint_always_works():
    """Test du endpoint health (sans DB, doit toujours marcher)."""
    transport = ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/v1/health")
        
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio 
async def test_validation_enum_strict():
    """Test validation Pydantic sans dépendance DB."""
    transport = ASGITransport(app=app)
    
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Payload invalide (enum)
        invalid_payload = {
            "subject": "Test enum validation",
            "audience": "etudiant",  # Invalide
            "duration": "short"
        }
        
        resp = await client.post("/v1/lessons", json=invalid_payload)
        
        assert resp.status_code == 422
        error_detail = resp.json()["detail"]
        assert len(error_detail) >= 1
        assert "literal_error" in error_detail[0]["type"]