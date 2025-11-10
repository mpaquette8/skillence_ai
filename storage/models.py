# // file: storage/models.py
"""
Modèles ORM simplifiés pour la base SQLite (MVP v0.2 – préparation front).

Contient les tables historiques (requests, lessons) et les nouvelles tables
front (users, login_tokens, sessions) utilisées par l’authentification lien
magique et Google OAuth.
"""

# Inventaire des dépendances
# - sqlalchemy (tierce) : colonnes SQL (String, Text, DateTime, ForeignKey, UniqueConstraint)
# - sqlalchemy.orm (tierce) : ORM 2.x (Mapped, mapped_column, relationship)
# - typing (stdlib) : collections optionnelles (List, Optional)
# - datetime (stdlib) : gestion de l’heure UTC (datetime, timezone)
# - uuid (stdlib) : génération d’identifiants uniques (uuid4)
# - json (stdlib) : sérialisation liste → JSON pour stockage SQLite
from sqlalchemy import String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime, timezone
from uuid import uuid4
import json

from .base import Base


def utcnow() -> datetime:
    """Retourne l’heure actuelle en UTC (helper unique pour tous les modèles)."""
    return datetime.now(timezone.utc)


class Request(Base):
    """
    Table "requests" : trace chaque demande utilisateur d’une leçon.

    Contient les paramètres d’entrée ainsi que le hash d’idempotence.
    """

    __tablename__ = "requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    input_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    subject: Mapped[str] = mapped_column(String(160), nullable=False)
    audience: Mapped[str] = mapped_column(String(32), nullable=False)
    duration: Mapped[str] = mapped_column(String(16), nullable=False)

    lessons: Mapped[List["Lesson"]] = relationship(
        back_populates="request",
        cascade="all, delete-orphan",
    )


class Lesson(Base):
    """
    Table "lessons" : contenu pédagogique généré (Markdown + plan).

    Stocke également la liste des objectifs et le plan sous forme JSON.
    """

    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), nullable=False)
    request: Mapped[Request] = relationship(back_populates="lessons")

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)

    _objectives_json: Mapped[str] = mapped_column("objectives", Text, nullable=False, default="[]")
    _plan_json: Mapped[str] = mapped_column("plan", Text, nullable=False, default="[]")

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


class User(Base):
    """
    Table "users" : comptes front (email + option Google).

    Email unique (minuscule) et identifiant Google (google_sub) pour relier
    un compte OAuth existant.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    email: Mapped[str] = mapped_column(String(160), unique=True, nullable=False, index=True)
    google_sub: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)

    login_tokens: Mapped[List["LoginToken"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sessions: Mapped[List["UserSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class LoginToken(Base):
    """
    Table "login_tokens" : liens magiques envoyés par e-mail.

    Utilisée pour le flux passwordless. Unicité garantie sur le token.
    """

    __tablename__ = "login_tokens"
    __table_args__ = (UniqueConstraint("token", name="uq_login_tokens_token"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    redeemed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    token: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="login_tokens")


class UserSession(Base):
    """
    Table "sessions" : sessions actives (cookie HTTP).

    Permet d’invalider les connexions lorsqu’un utilisateur se déconnecte.
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user: Mapped["User"] = relationship(back_populates="sessions")

