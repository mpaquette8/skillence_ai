# // file: tests/test_web_dashboard.py
"""
Tests d'intégration pour le tableau de bord web (liste + génération de leçons).
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de test async
# - httpx (tierce) : client HTTP pour FastAPI
# - unittest.mock (stdlib) : patch des services
# - tempfile/pathlib (stdlib) : DB SQLite temporaire
# - sqlalchemy (tierce) : moteur + sessionmaker
# - datetime (stdlib) : timestamps pour les leçons
# - contextlib (stdlib) : contextmanager pour get_session
# - api.main (local) : application FastAPI complète
# - storage.base/models (local) : Base, modèles ORM
# - web.routes (local) : constante cookie
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
from storage.models import (
    User,
    LoginToken,
    Lesson,
    Request as LessonRequestModel,
    UserSession,
)
from web.routes import SESSION_COOKIE_NAME


@pytest.fixture
def web_app_with_db():
    """Application FastAPI montée sur une base temporaire isolée."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "dashboard.db"
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
                 patch("web.routes.get_session", _session_override), \
                 patch("api.services.lessons.get_session", _session_override):
                yield app, TestSessionLocal

            engine.dispose()


async def _login(client: httpx.AsyncClient, session_factory) -> None:
    """Effectue le flux lien magique pour obtenir le cookie de session."""
    await client.post(
        "/web/login",
        data={"email": "dashboard@example.com"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with session_factory() as db:
        token = db.execute(select(LoginToken)).scalars().first()
        token_value = token.token

    resp = await client.get(
        f"/web/login/callback?token={token_value}",
        follow_redirects=False,
    )
    session_cookie = resp.cookies[SESSION_COOKIE_NAME]
    client.cookies.set(SESSION_COOKIE_NAME, session_cookie)


@pytest.mark.asyncio
async def test_dashboard_empty_state(web_app_with_db):
    app_instance, SessionLocal = web_app_with_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _login(client, SessionLocal)

        resp = await client.get("/web/dashboard")

    assert resp.status_code == 200
    assert "Aucune leçon disponible" in resp.text


@pytest.mark.asyncio
async def test_dashboard_lists_latest_lessons(web_app_with_db):
    app_instance, SessionLocal = web_app_with_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    base_time = datetime.now(timezone.utc) - timedelta(hours=1)
    with SessionLocal() as db:

        user = User(email="dashboard@example.com")
        db.add(user)
        db.flush()
        session = UserSession(
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(session)

        for idx in range(12):
            req = LessonRequestModel(
                subject=f"Sujet {idx}",
                audience="lycéen",
                duration="short",
                input_hash=f"hash-{idx}",
            )
            db.add(req)
            db.flush()

            lesson = Lesson(
                request_id=req.id,
                title=f"Titre {idx}",
                content_md=f"Contenu {idx}",
            )
            lesson.objectives = ["Obj"]
            lesson.plan = ["Plan"]
            lesson.created_at = base_time + timedelta(minutes=idx)
            db.add(lesson)
        db.commit()

    with SessionLocal() as db:
        assert db.query(Lesson).count() == 12

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _login(client, SessionLocal)
        resp = await client.get("/web/dashboard")

        assert resp.status_code == 200
        assert "Titre 11" in resp.text
        assert "Titre 10" in resp.text
        assert "Titre 0" not in resp.text  # les deux plus anciens hors top 10
        assert "?page=2" in resp.text

        resp_page2 = await client.get("/web/dashboard?page=2")
        assert resp_page2.status_code == 200
        assert "Titre 1" in resp_page2.text
        assert "Titre 11" not in resp_page2.text


@pytest.mark.asyncio
async def test_dashboard_post_generates_lesson(web_app_with_db):
    app_instance, SessionLocal = web_app_with_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _login(client, SessionLocal)

        with patch("web.routes.create_lesson") as mock_create:
            mock_create.return_value = {
                "lesson_id": "fake-id",
                "title": "fake",
                "quality": {},
                "tokens_used": 0,
                "from_cache": False,
            }

            resp = await client.post(
                "/web/dashboard",
                data={
                    "subject": "Gravitation",
                    "audience": "lycéen",
                    "duration": "short",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                follow_redirects=False,
            )

    assert resp.status_code == 303
    assert resp.headers["Location"] == "/web/dashboard?message=lesson_created"
    mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_lesson_detail_page(web_app_with_db):
    app_instance, SessionLocal = web_app_with_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    with SessionLocal() as db:
        req = LessonRequestModel(
            subject="Photosynthèse",
            audience="lycéen",
            duration="short",
            input_hash="detail-hash",
        )
        db.add(req)
        db.flush()

        lesson = Lesson(
            request_id=req.id,
            title="Photosynthèse (niveau lycéen)",
            content_md="# Titre\n\nContenu test.",
        )
        lesson.objectives = ["Comprendre"]
        lesson.plan = ["Étape 1", "Étape 2"]
        db.add(lesson)
        db.flush()
        lesson_id = lesson.id
        db.commit()

    with SessionLocal() as db:
        assert db.query(Lesson).count() == 1

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _login(client, SessionLocal)
        resp = await client.get(f"/web/lessons/{lesson_id}")

    assert resp.status_code == 200
    assert "<h1>Titre</h1>" in resp.text
    assert "<li>Comprendre</li>" in resp.text
    assert "<li>Étape 1</li>" in resp.text


@pytest.mark.asyncio
async def test_lesson_detail_missing_returns_404(web_app_with_db):
    app_instance, SessionLocal = web_app_with_db
    transport = ASGITransport(app=app_instance, raise_app_exceptions=False)

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _login(client, SessionLocal)
        resp = await client.get("/web/lessons/inconnu")

    assert resp.status_code == 404
