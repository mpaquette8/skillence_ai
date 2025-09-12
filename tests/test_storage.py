# // file: skillence_ai/tests/test_storage.py
"""
Tests CRUD sur SQLite temporaire (fichier).
"""

# Inventaire des dépendances
# - tempfile (stdlib) : fichier temporaire pour DB
# - pathlib (stdlib) : manipulation chemins
# - sqlalchemy (tierce) : create_engine + Session pour test isolé
# - sqlalchemy.orm (tierce) : sessionmaker
# - typing (stdlib) : annotations
# - skillence_ai.storage.base (local) : Base pour create_all
# - skillence_ai.storage.models (local) : ORM Request, Lesson
import tempfile  # stdlib — DB temporaire
from pathlib import Path  # stdlib — gestion de chemins
from sqlalchemy import create_engine  # tierce — moteur test
from sqlalchemy.orm import sessionmaker, Session  # tierce — session
from typing import List  # stdlib — hints

from storage.base import Base
from storage.models import Request, Lesson


def test_storage_crud_roundtrip() -> None:
    """Création des tables + insertion & lecture Request/Lesson."""
    # DB temporaire isolée
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        TestingSession = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)

        # Init schema
        Base.metadata.create_all(bind=engine)

        # Insert
        with TestingSession() as db:
            req = Request(subject="La photosynthèse", audience="lycéen", duration="short")
            db.add(req)
            db.flush()  # avoir req.id

            lesson = Lesson(
                request_id=req.id,
                title="La photosynthèse",
                content_md="# La photosynthèse\n\nContenu...",
            )
            lesson.objectives = ["Comprendre le rôle du soleil", "Identifier les étapes"]
            lesson.plan = ["Introduction", "Étapes", "Importance"]
            lesson.quiz = [{"question": "…", "choices": ["A", "B"], "answer": 0, "rationale": "…"}]

            db.add(lesson)
            db.commit()

        # Read-back
        with TestingSession() as db:
            l: Lesson = db.query(Lesson).first()  # type: ignore[assignment]
            assert l.title == "La photosynthèse"
            assert isinstance(l.objectives, list) and len(l.objectives) == 2
            assert l.plan == ["Introduction", "Étapes", "Importance"]
            assert isinstance(l.quiz, list) and len(l.quiz) == 1

            # Relation
            r: Request = db.query(Request).first()  # type: ignore[assignment]
            assert len(r.lessons) == 1
            assert r.lessons[0].id == l.id
