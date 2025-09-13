# // file: storage/base.py
"""
Base et bootstrap SQLAlchemy avec validation de config (MVP v0.1, SQLite).
Valide la configuration OpenAI au démarrage pour éviter les erreurs silencieuses.
"""

# Inventaire des dépendances
# - pydantic_settings (tierce) : charge config depuis .env — validation automatique
# - sqlalchemy (tierce) : ORM et moteur DB — alternative: SQL brut mais moins pratique
# - sqlalchemy.orm (tierce) : sessions et DeclarativeBase — nécessaire pour ORM moderne 2.x
# - contextlib (stdlib) : gestionnaire de contexte with/as — alternative: try/finally mais plus verbeux
# - typing (stdlib) : annotations de types Iterator — améliore lisibilité
# - logging (stdlib) : logs structurés — alternative: print() mais pas configurable
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("skillence_ai.config")


class Settings(BaseSettings):
    """Configuration de l'application avec validation."""
    
    # Base de données (SQLite par défaut)
    DATABASE_URL: str = "sqlite:///./skillence_ai.db"
    
    # OpenAI (obligatoire)
    OPENAI_API_KEY: str = ""
    OPENAI_TIMEOUT: int = 15
    
    # Logging
    LOG_LEVEL: str = "INFO"
    DEBUG_MODE: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore les variables d'env non définies
    )
    
    def validate_openai_config(self) -> None:
        """Valide la configuration OpenAI au démarrage."""
        if not self.OPENAI_API_KEY:
            raise ValueError(
                "❌ OPENAI_API_KEY manquante!\n"
                "💡 Solution: copiez .env.example vers .env et ajoutez votre clé OpenAI\n"
                "🔗 Récupérez une clé sur https://platform.openai.com/api-keys"
            )
        
        if not self.OPENAI_API_KEY.startswith("sk-"):
            raise ValueError(
                f"❌ OPENAI_API_KEY invalide: {self.OPENAI_API_KEY[:10]}...\n" 
                "💡 Une clé OpenAI valide commence par 'sk-'"
            )
        
        if self.OPENAI_TIMEOUT < 5 or self.OPENAI_TIMEOUT > 60:
            logger.warning(f"⚠️ OPENAI_TIMEOUT={self.OPENAI_TIMEOUT}s semble incorrect (recommandé: 10-30s)")
        
        logger.info(f"✅ Configuration OpenAI validée (timeout={self.OPENAI_TIMEOUT}s)")


# Instance globale des settings
settings = Settings()


class Base(DeclarativeBase):
    """Classe de base pour tous les modèles ORM."""
    pass


# Moteur SQLAlchemy avec configuration
engine = create_engine(
    settings.DATABASE_URL, 
    future=True,
    echo=settings.DEBUG_MODE  # Log SQL si debug activé
)

# Factory de sessions
SessionLocal = sessionmaker(
    bind=engine, 
    class_=Session, 
    autoflush=False, 
    autocommit=False, 
    future=True
)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Gestionnaire de contexte pour les sessions DB.
    Usage: 
        with get_session() as db:
            db.add(obj)
            # commit automatique si pas d'erreur
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialise la base de données et valide la configuration.
    
    Étapes:
    1. Valide config OpenAI
    2. Crée les tables si nécessaires
    3. Log confirmation
    """
    # 1. Validation de config
    settings.validate_openai_config()
    
    # 2. Import des modèles pour créer les tables
    from . import models as _models
    _ = _models  # Évite le warning "unused import"
    
    # 3. Création des tables
    Base.metadata.create_all(bind=engine)
    
    # 4. Log confirmation
    table_count = len(Base.metadata.tables)
    logger.info(f"✅ Base de données initialisée ({table_count} tables créées)")
    logger.info(f"🗄️ DB: {settings.DATABASE_URL}")


def get_db_stats() -> dict:
    """
    Retourne des statistiques simples sur la base (optionnel, pour debug).
    """
    with get_session() as db:
        from .models import Request, Lesson
        
        request_count = db.query(Request).count()
        lesson_count = db.query(Lesson).count()
        
        return {
            "requests": request_count,
            "lessons": lesson_count,
            "database_url": settings.DATABASE_URL
        }