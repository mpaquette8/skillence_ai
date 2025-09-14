# // file: tests/test_config.py

"""
Configuration de test ISOLÉE (sans OpenAI requis).
Contourne la validation de clé API pour les tests automatisés.
"""

# Inventaire des dépendances
# - pytest (tierce) : fixture de configuration — setup test environment
# - unittest.mock (stdlib) : patch temporaire — remplace comportement validation
# - tempfile (stdlib) : DB temporaire — isolation tests
# - pathlib (stdlib) : manipulation chemins — gestion fichiers temporaires
# - sqlalchemy (tierce) : moteur test — DB en mémoire
# - storage.base (local) : Settings, Base — configuration et schéma
import pytest
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from storage.base import Settings, Base


@pytest.fixture(scope="session")
def test_settings():
    """Settings de test avec clé OpenAI mockée."""
    return Settings(
        DATABASE_URL="sqlite:///./test.db",
        OPENAI_API_KEY="sk-test-key-for-mocking-1234567890abcdef",  # Clé factice valide
        OPENAI_TIMEOUT=15,
        LOG_LEVEL="ERROR",  # Réduire le bruit dans les tests
        DEBUG_MODE=False
    )


@pytest.fixture(scope="session")
def mock_openai_validation():
    """
    Désactive la validation OpenAI pour tous les tests d'API.
    Patch la méthode validate_openai_config() pour qu'elle ne fasse rien.
    """
    with patch('storage.base.Settings.validate_openai_config', return_value=None):
        yield


@pytest.fixture
def test_db_engine():
    """
    Engine de test avec DB temporaire (isolation complète).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_api.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True, echo=False)
        
        # Créer le schéma
        Base.metadata.create_all(bind=engine)
        
        yield engine
        
        # Nettoyage
        engine.dispose()


@pytest.fixture
def test_session_factory(test_db_engine):
    """Factory de sessions pour les tests d'API."""
    return sessionmaker(
        bind=test_db_engine, 
        class_=Session, 
        autoflush=False, 
        autocommit=False, 
        future=True
    )