"""
Modèles ORM SIMPLIFIÉS (sans quiz) - MVP v0.1.2.

NETTOYAGE v0.1.2:
- Suppression du champ quiz dans Lesson
- Maintien des champs essentiels (objectives, plan)
- JSON storage optimisé pour SQLite/Postgres
"""

# Inventaire des dépendances
# - sqlalchemy (tierce) : types de colonnes — String, Text, DateTime, ForeignKey
# - sqlalchemy.orm (tierce) : ORM moderne 2.x — Mapped, mapped_column, relationship
# - typing (stdlib) : types optionnels — List, Optional
# - datetime (stdlib) : gestion dates UTC — datetime, timezone
# - uuid (stdlib) : identifiants uniques — uuid4 pour clés primaires
# - json (stdlib) : sérialisation Python/JSON — stockage listes en SQLite
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4
import json

from .base import Base


def utcnow() -> datetime:
    """Retourne l'heure actuelle en UTC."""
    return datetime.now(timezone.utc)


class Request(Base):
    """
    Table "requests" : demandes utilisateur.
    Champs: sujet, audience, durée, hash (idempotence).
    """

    __tablename__ = "requests"

    # Identifiant unique (UUID)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Date de création (UTC)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Hash pour idempotence
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Paramètres utilisateur
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False)
    duration: Mapped[str] = mapped_column(String(16), nullable=False)

    # Relation : une requête → plusieurs leçons (1..n)
    lessons: Mapped[List["Lesson"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class Lesson(Base):
    """
    Table "lessons" : leçons générées (SANS QUIZ).
    
    SIMPLIFICATION v0.1.2:
    - Suppression du champ _quiz_json
    - Focus sur title, content_md, objectives, plan
    """

    __tablename__ = "lessons"

    # Identifiant unique
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # Date de création
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Clé étrangère : lien vers Request
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    request: Mapped[Request] = relationship(back_populates="lessons")

    # Contenu principal
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)

    # Champs JSON stockés comme texte (compatibilité SQLite)
    _objectives_json: Mapped[str] = mapped_column("objectives", Text, nullable=False, default="[]")
    _plan_json: Mapped[str] = mapped_column("plan", Text, nullable=False, default="[]")
    
    # SUPPRIMÉ: _quiz_json (reporté v0.2)

    # Propriétés Python pour manipulation facile
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