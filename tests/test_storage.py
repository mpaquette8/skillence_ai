"""
Tests CRUD CORRIGÉS (sans quiz) - Version Windows compatible - v0.1.2.

CORRECTIFS:
- Suppression de toutes les références quiz
- Focus sur objectives + plan uniquement
- Test isolation maintenu
"""

# Inventaire des dépendances
# - tempfile (stdlib) : fichier temporaire pour DB — isolation tests
# - pathlib (stdlib) : manipulation chemins — alternative: os.path mais moins lisible
# - sqlalchemy (tierce) : create_engine + Session pour test isolé — moteur DB
# - sqlalchemy.orm (tierce) : sessionmaker — factory sessions
# - typing (stdlib) : annotations — améliore lisibilité
# - storage.base (local) : Base pour create_all — schéma DB
# - storage.models (local) : ORM Request, Lesson — modèles à tester
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List

from storage.base import Base
from storage.models import Request, Lesson


def test_storage_crud_roundtrip():
    """
    Création des tables + insertion & lecture Request/Lesson (SANS QUIZ).
    Windows compatible avec nettoyage manuel.
    """
    # DB temporaire isolée
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        TestingSession = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False, future=True)

        try:
            # Init schema
            Base.metadata.create_all(bind=engine)

            # Insert Request + Lesson (SANS QUIZ)
            with TestingSession() as db:
                req = Request(subject="La photosynthèse", audience="lycéen", duration="short")
                db.add(req)
                db.flush()  # avoir req.id

                lesson = Lesson(
                    request_id=req.id,
                    title="La photosynthèse expliquée",
                    content_md="# La photosynthèse\n\n## Contenu\nLa photosynthèse est...",
                )
                lesson.objectives = ["Comprendre le rôle du soleil", "Identifier les étapes"]
                lesson.plan = ["Introduction", "Étapes", "Importance écologique"]
                # SUPPRIMÉ: lesson.quiz = [...]

                db.add(lesson)
                db.commit()

            # Read-back et vérifications
            with TestingSession() as db:
                l: Lesson = db.query(Lesson).first()  # type: ignore[assignment]
                assert l.title == "La photosynthèse expliquée"
                assert isinstance(l.objectives, list) and len(l.objectives) == 2
                assert l.plan == ["Introduction", "Étapes", "Importance écologique"]
                assert l.content_md.startswith("# La photosynthèse")
                
                # SUPPRIMÉ: assert isinstance(l.quiz, list) and len(l.quiz) == 1

                # Relation Request → Lesson
                r: Request = db.query(Request).first()  # type: ignore[assignment]
                assert len(r.lessons) == 1
                assert r.lessons[0].id == l.id
                assert r.subject == "La photosynthèse"

        finally:
            # Fermeture explicite des connexions pour Windows
            engine.dispose()
            
            # Nettoyage manuel si nécessaire
            try:
                if db_path.exists():
                    os.chmod(db_path, 0o777)  
                    db_path.unlink()  
            except (OSError, PermissionError):
                pass  # Ignore les erreurs de nettoyage


def test_lesson_properties_json_storage():
    """
    Test spécifique du stockage JSON des propriétés (objectives, plan).
    Vérifie que la sérialisation/désérialisation fonctionne correctement.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_props.db"
        engine = create_engine(f"sqlite:///{db_path}", future=True)
        TestingSession = sessionmaker(bind=engine, class_=Session, future=True)

        try:
            Base.metadata.create_all(bind=engine)

            # Test avec données complexes (accents, caractères spéciaux)
            with TestingSession() as db:
                req = Request(subject="Test propriétés", audience="adulte", duration="medium")
                db.add(req)
                db.flush()

                lesson = Lesson(
                    request_id=req.id,
                    title="Test élémentaire",
                    content_md="# Test\nContenu avec **gras** et _italique_"
                )
                
                # Test objectives avec accents et caractères spéciaux
                lesson.objectives = [
                    "Comprendre les phénomènes électriques", 
                    "Maîtriser l'usage des formules (P = U × I)",
                    "Évaluer les risques & sécurité"
                ]
                
                # Test plan avec numérotation et caractères spéciaux
                lesson.plan = [
                    "1. Introduction : qu'est-ce que l'électricité ?",
                    "2. Lois fondamentales (Ohm & Joule)", 
                    "3. Applications pratiques",
                    "4. Exercices & évaluation"
                ]

                db.add(lesson)
                db.commit()

            # Vérification lecture
            with TestingSession() as db:
                lesson_read = db.query(Lesson).first()
                
                # Vérifications objectives
                assert len(lesson_read.objectives) == 3
                assert "électriques" in lesson_read.objectives[0]
                assert "P = U × I" in lesson_read.objectives[1] 
                assert "sécurité" in lesson_read.objectives[2]
                
                # Vérifications plan
                assert len(lesson_read.plan) == 4
                assert lesson_read.plan[0].startswith("1. Introduction")
                assert "Ohm & Joule" in lesson_read.plan[1]
                assert "évaluation" in lesson_read.plan[3]

        finally:
            engine.dispose()
            try:
                if db_path.exists():
                    db_path.unlink()
            except:
                pass