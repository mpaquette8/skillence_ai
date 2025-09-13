# // file: skillence_ai/storage/models.py
"""
Modèles ORM (MVP v0.1).
Ici, on décrit les "tables" de la base de données sous forme de classes Python.
Chaque ligne d'une table = un objet de cette classe.

- Request : correspond à la demande de l’utilisateur (sujet, audience, durée).
- Lesson : correspond à la leçon générée (titre, contenu markdown, plan, quiz).
"""

# Inventaire des dépendances
# - sqlalchemy (tierce) : sert à définir les colonnes des tables (String, Text, etc.)
# - sqlalchemy.orm (tierce) : sert à décrire les classes comme des tables (ORM moderne 2.x)
# - typing (stdlib) : précise les types attendus (List, Optional) → aide mypy/pyright
# - datetime (stdlib) : permet d’avoir des dates/horaires corrects (UTC, portable)
# - uuid (stdlib) : génère des identifiants uniques (UUID v4) au lieu d’IDs auto-incrémentés
# - json (stdlib) : on s’en sert pour stocker des listes dans SQLite (qui n’a pas de type JSON natif)

from sqlalchemy import String, Text, DateTime, ForeignKey  # types de colonnes pour les champs
from sqlalchemy.orm import Mapped, mapped_column, relationship  # "colle" nos classes Python aux tables SQL
from typing import List, Optional  # sert à dire qu’une valeur peut être absente (Optional) ou une liste
from datetime import datetime, timezone  # pour gérer les dates en UTC
from uuid import uuid4  # génère un identifiant unique sous forme de chaîne
import json  # permet de transformer Python <-> texte (utile car SQLite n’a pas JSON natif)

from .base import Base  # notre "base commune" définie dans base.py


def utcnow() -> datetime:
    """Retourne l’heure actuelle en UTC (utilisé comme valeur par défaut)."""
    return datetime.now(timezone.utc)


class Request(Base):
    """
    Table "requests" : chaque ligne = une demande de l’utilisateur.
    On y garde la trace de ce que l’utilisateur a demandé :
    - sujet, audience (enfant/lycéen/adulte), durée (short/medium/long)
    - hash (optionnel) pour éviter de régénérer deux fois la même leçon
    """

    __tablename__ = "requests"

    # Identifiant unique (UUID stocké en string pour compatibilité SQLite/Postgres)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Date de création (UTC)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Pour l’idempotence (vérifier si une requête identique a déjà été faite)
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Les paramètres donnés par l’utilisateur
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False)  # ex: enfant / lycéen / adulte
    duration: Mapped[str] = mapped_column(String(16), nullable=False)  # ex: short / medium / long

    # Relation : une requête peut donner naissance à plusieurs leçons (1..n)
    lessons: Mapped[List["Lesson"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class Lesson(Base):
    """
    Table "lessons" : chaque ligne = une leçon générée.
    Elle contient :
    - le titre de la leçon
    - le contenu au format Markdown
    - des champs optionnels (plan, objectifs, quiz) stockés en JSON (texte)
    """

    __tablename__ = "lessons"

    # Identifiant unique
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Date de création
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Clé étrangère : à quelle requête appartient cette leçon ?
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    request: Mapped[Request] = relationship(back_populates="lessons")

    # Contenu principal
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)

    # Champs JSON stockés comme texte pour compatibilité SQLite
    _objectives_json: Mapped[str] = mapped_column("objectives", Text, nullable=False, default="[]")
    _plan_json: Mapped[str] = mapped_column("plan", Text, nullable=False, default="[]")
    _quiz_json: Mapped[str] = mapped_column("quiz", Text, nullable=False, default="[]")

    # Propriétés Python : permettent d’utiliser directement des listes/dicos côté code
    @property
    def objectives(self) -> List[str]:
        return json.loads(self._objectives_json or "[]")

    @objectives.setter
    def objectives(self, value: List[str]) -> None:
        self._objectives_json = json.dumps(value, ensure_ascii=False)

    @property
    def plan(self) -> List[str]:
        return json.loads(self._plan_json or "[]")

    @plan.setter
    def plan(self, value: List[str]) -> None:
        self._plan_json = json.dumps(value, ensure_ascii=False)

    @property
    def quiz(self) -> List[dict]:
        return json.loads(self._quiz_json or "[]")

    @quiz.setter
    def quiz(self, value: List[dict]) -> None:
        self._quiz_json = json.dumps(value, ensure_ascii=False)
