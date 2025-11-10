# // file: tests/test_web_auth.py
"""
Tests d’intégration pour le flux lien magique HTML (v0.2).
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de test async
# - httpx (tierce) : client HTTP pour FastAPI (ASGITransport)
# - unittest.mock (stdlib) : patch des sessions DB
# - tempfile (stdlib) : création de dossiers temporaires pour SQLite
# - pathlib (stdlib) : manipulation de chemins
# - sqlalchemy (tierce) : moteur + sessionmaker pour DB isolée
# - datetime (stdlib) : gestion des dates pour tokens expirés
# - api.main (local) : application FastAPI complète
# - storage.base (local) : Base pour créer les tables
# - storage.models (local) : classes User, LoginToken pour assertions
# - web.routes (local) : constantes (SESSION_COOKIE_NAME)
import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import patch
import tempfile
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

from api.main import app
from storage.base import Base
from storage.models import User, LoginToken, UserSession
from web.routes import SESSION_COOKIE_NAME


@pytest.fixture
def web_app_with_isolated_db():
    """Applique l’application sur une base SQLite temporaire et isolée."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "web_auth.db"
        db_url = f"sqlite:///{db_path}"

        with patch("storage.base.settings.DATABASE_URL", db_url):
            engine = create_engine(db_url, future=True)
            Base.metadata.create_all(bind=engine)
            TestSessionLocal = sessionmaker(bind=engine, class_=Session, future=True)

            @contextmanager
            def _session_override():
                db = TestSessionLocal()
                try:
                    yield db
                    db.commit()
                except Exception:
                    db.rollback()
                    raise
                finally:
                    db.close()

            with patch("storage.base.SessionLocal", TestSessionLocal), \
                 patch("storage.base.get_session", _session_override), \
                 patch("web.routes.get_session", _session_override):

                yield app, TestSessionLocal

            engine.dispose()


@pytest.mark.asyncio
async def test_request_magic_link_creates_token(web_app_with_isolated_db):
    app_instance, SessionLocal = web_app_with_isolated_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/web/login",
            data={"email": "User@example.com"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    assert resp.status_code == 200
    assert "Lien envoyé" in resp.text

    with SessionLocal() as db:
        user_count = db.execute(select(User)).scalars().all()
        tokens = db.execute(select(LoginToken)).scalars().all()
        assert len(user_count) == 1
        assert len(tokens) == 1
        assert tokens[0].user_id == user_count[0].id


@pytest.mark.asyncio
async def test_callback_creates_session_and_redirects(web_app_with_isolated_db):
    app_instance, SessionLocal = web_app_with_isolated_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/web/login",
            data={"email": "demo@example.com"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    with SessionLocal() as db:
        token = db.execute(select(LoginToken)).scalars().first()
        token_value = token.token

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        callback_resp = await client.get(f"/web/login/callback?token={token_value}", follow_redirects=False)

    assert callback_resp.status_code == 303
    assert SESSION_COOKIE_NAME in callback_resp.cookies
    session_cookie = callback_resp.cookies[SESSION_COOKIE_NAME]

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE_NAME, session_cookie)
        dashboard = await client.get("/web/dashboard")

    assert dashboard.status_code == 200
    assert "Bienvenue, <strong>demo@example.com</strong>" in dashboard.text

    with SessionLocal() as db:
        sessions = db.execute(select(UserSession)).scalars().all()
        assert len(sessions) == 1
        assert sessions[0].user.email == "demo@example.com"


@pytest.mark.asyncio
async def test_callback_rejects_expired_token(web_app_with_isolated_db):
    app_instance, SessionLocal = web_app_with_isolated_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    with SessionLocal() as db:
        user = User(email="expired@example.com")
        db.add(user)
        db.flush()
        expired = LoginToken(
            user_id=user.id,
            token="expired-token",
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        db.add(expired)
        db.commit()

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/web/login/callback?token=expired-token")

    assert resp.status_code == 400
    assert "Lien expiré" in resp.text
