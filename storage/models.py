# // file: skillence_ai/storage/models.py
"""
Modèles ORM (MVP v0.1):
- Request: entrée utilisateur + hash d'idempotence (facultatif pour plus tard)
- Lesson: sortie formatée (markdown + méta)
"""

# Inventaire des dépendances
# - sqlalchemy (tierce) : types de colonnes (String, Text, DateTime, ForeignKey)
# - sqlalchemy.orm (tierce) : Mapped/mapped_column pour ORM 2.x
# - typing (stdlib) : annotations (List, Optional)
# - datetime (stdlib) : timestamps UTC
# - uuid (stdlib) : génération d'identifiants (UUID v4)
# - json (stdlib) : sérialisation manuelle pour listes (SQLite sans JSON natif)
from sqlalchemy import String, Text, DateTime, ForeignKey  # tierce — types de colonnes
from sqlalchemy.orm import Mapped, mapped_column, relationship  # tierce — ORM 2.x typing
from typing import List, Optional  # stdlib — types
from datetime import datetime, timezone  # stdlib — timestamps UTC
from uuid import uuid4  # stdlib — ids uniques
import json  # stdlib — sérialisation JSON (SQLite)

from .base import Base  # local — base déclarative


def utcnow() -> datetime:
    """Retourne un datetime UTC (naive->aware)."""
    return datetime.now(timezone.utc)


class Request(Base):
    """Requête utilisateur qui déclenche une génération de leçon."""

    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Idempotence simple (optionnelle en v0.1, prête pour v0.2)
    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True, unique=False)

    # Trace minimale de l'entrée
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False)  # ex: enfant/lycéen/adulte
    duration: Mapped[str] = mapped_column(String(16), nullable=False)  # ex: short/medium/long

    # Relation 1..n vers Lesson
    lessons: Mapped[List["Lesson"]] = relationship(back_populates="request", cascade="all, delete-orphan")


class Lesson(Base):
    """Leçon générée et stockée (markdown + méta)."""

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    request: Mapped[Request] = relationship(back_populates="lessons")

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)

    # Stockage JSON (listes) via TEXT pour compat SQLite; simple et portable.
    _objectives_json: Mapped[str] = mapped_column("objectives", Text, nullable=False, default="[]")
    _plan_json: Mapped[str] = mapped_column("plan", Text, nullable=False, default="[]")
    _quiz_json: Mapped[str] = mapped_column("quiz", Text, nullable=False, default="[]")

    # Propriétés de confort (sérialisation JSON manuelle)
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
