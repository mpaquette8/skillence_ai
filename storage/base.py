# // file: skillence_ai/storage/base.py
"""
Base et bootstrap SQLAlchemy (MVP v0.1, SQLite sync).
- Fournit: engine, SessionLocal (context manager), Base (declarative), init_db()
- Config via pydantic-settings (DATABASE_URL), défaut SQLite local.
"""

# Inventaire des dépendances
# - pydantic_settings (tierce) : gestion de config 12-factor (.env) — alternative: os.getenv + dataclass
# - sqlalchemy (tierce) : ORM 2.x, engine sync — alternative async: aiosqlite + SQLAlchemy async (v0.2+)
# - sqlalchemy.orm (tierce) : base déclarative & session
# - contextlib (stdlib) : contextmanager pour encapsuler la session
# - typing (stdlib) : annotations de types
from pydantic_settings import BaseSettings  # tierce — configuration via variables d'environnement
from sqlalchemy import create_engine  # tierce — fabrique de moteur DB (sync)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session  # tierce — ORM 2.x
from contextlib import contextmanager  # stdlib — gestion contextuelle de la session
from typing import Iterator  # stdlib — type pour générateur


class Settings(BaseSettings):
    """Paramètres d'application (DB, etc.)."""

    DATABASE_URL: str = "sqlite:///./skillence_ai.db"  # défaut local (sync)
    # Note: pas de secrets en dur (OpenAI key etc. dans .env à part)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy (ORM 2.x)."""

    pass


# Engine sync (SQLite fichier). echo=False par défaut (logs SQL désactivés en prod).
engine = create_engine(settings.DATABASE_URL, future=True)


# Session factory (autocommit=False, autoflush=False pour contrôle explicite).
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Contexte de session DB.
    Usage:
        with get_session() as db:
            ...
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
    """Crée les tables si absentes (MVP v0.1 — Alembic plus tard)."""
    # Import tardif pour éviter import cycles
    from . import models as _models

    _ = _models  # satisfare l'analyseur statique (référence utilisée)
    Base.metadata.create_all(bind=engine)
