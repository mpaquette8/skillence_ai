# // file: skillence_ai/storage/base.py
"""
Base et bootstrap SQLAlchemy (MVP v0.1, SQLite sync).
Ici on prépare tout ce qui est nécessaire pour parler avec la base de données.
- On configure l’adresse de la base (par défaut SQLite local).
- On définit la "Base" pour créer nos tables.
- On fabrique un moteur (engine) qui sait ouvrir/fermer la DB.
- On crée une "Session" (carnet temporaire) pour lire/écrire dans la DB.
- On ajoute un helper init_db() pour créer les tables si elles n’existent pas.
"""

# Inventaire des dépendances
# - pydantic_settings (tierce) : permet de charger la config depuis .env (plus pratique que coder en dur)
# - sqlalchemy (tierce) : outil pour parler à la base (ici SQLite) de manière haut niveau
# - sqlalchemy.orm (tierce) : partie ORM qui gère les tables comme des classes Python
# - contextlib (stdlib) : permet de créer un "with ... as ..." pour ouvrir/fermer automatiquement une session
# - typing (stdlib) : donne le type Iterator (utile pour dire qu’on retourne un générateur de sessions)

from pydantic_settings import BaseSettings  # charge la config depuis les variables d'environnement (.env)
from sqlalchemy import create_engine  # crée le "moteur" pour se connecter à la DB
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session  # outils ORM pour gérer classes/tables et sessions
from contextlib import contextmanager  # permet d’écrire un contexte "with"
from typing import Iterator  # sert juste à dire qu’on retourne un générateur de sessions


class Settings(BaseSettings):
    """Paramètres d'application (notamment la connexion DB)."""

    # Par défaut : un fichier SQLite local. Pratique pour démarrer sans rien installer.
    DATABASE_URL: str = "sqlite:///./skillence_ai.db"
    OPENAI_API_KEY: str = ""

    class Config:
        # On lit un fichier `.env` si présent, pour surcharger cette valeur
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


class Base(DeclarativeBase):
    """Classe de base pour déclarer nos tables.
    Exemple : chaque modèle (Lesson, Request, etc.) héritera de cette classe.
    """
    pass


# Le "moteur" qui ouvre une connexion vers la DB (ici SQLite en mode fichier local).
# echo=False → pas de logs SQL dans la console (plus propre en prod).
engine = create_engine(settings.DATABASE_URL, future=True)


# Fabrique de sessions : une session = un petit carnet temporaire pour lire/écrire.
# autoflush/autocommit désactivés → on contrôle nous-mêmes quand on enregistre.
SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Donne une session prête à l'emploi sous forme de contexte.
    Exemple d’usage :
        with get_session() as db:
            db.add(objet)
            ...
    Avantages : la session est toujours correctement fermée,
    et si une erreur arrive → rollback automatique.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()  # si erreur → on annule ce qu’on a commencé
        raise
    finally:
        db.close()  # fermeture propre, sinon fuite de connexion


def init_db() -> None:
    """
    Crée les tables définies dans models.py si elles n’existent pas encore.
    Utile au démarrage du projet (MVP v0.1).
    Plus tard, on utilisera Alembic pour les migrations versionnées.
    """
    from . import models as _models  # import tardif pour éviter un cycle d’import

    _ = _models  # juste pour signaler à l’éditeur/linter que c’est bien utilisé
    Base.metadata.create_all(bind=engine)
