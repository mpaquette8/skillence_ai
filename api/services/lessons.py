# // file: api/services/lessons.py

"""
Service d'orchestration : agent lesson_generator + persistance SQLite.

Rôle :
- Recevoir une demande de leçon (LessonRequest)
- Appeler l'agent lesson_generator 
- Persister en base (Request + Lesson)
- Retourner les données pour la réponse API

Pourquoi un service séparé :
- Découple la logique métier des routes FastAPI
- Facilite les tests unitaires 
- Prépare l'évolution vers multi-agents (v0.2)
"""

# Inventaire des dépendances
# - hashlib (stdlib) : hash SHA-256 pour idempotence — alternative: uuid mais moins prévisible
# - json (stdlib) : sérialisation pour hash stable — alternative: pickle mais non portable
# - typing (stdlib) : annotations de types (Dict, Optional)
# - agents.lesson_generator (local) : DTOs + logique de génération
# - storage.base (local) : session DB + init
# - storage.models (local) : ORM Request/Lesson
import hashlib  # stdlib — hash pour idempotence
import json  # stdlib — sérialisation stable
from typing import Dict, Optional  # stdlib — typing

from agents.lesson_generator import LessonRequest, LessonContent, generate_lesson  # local — agent
from storage.base import get_session  # local — session DB
from storage.models import Request, Lesson  # local — ORM


def _compute_request_hash(request: LessonRequest) -> str:
    """
    Calcule un hash SHA-256 stable pour l'idempotence.
    
    Permet d'éviter de regénérer la même leçon plusieurs fois.
    Le hash est basé sur subject+audience+duration (ordre stable via sorted).
    """
    # Dictionnaire ordonné pour hash stable
    data = {
        "subject": request.subject.strip().lower(),
        "audience": request.audience.strip().lower(), 
        "duration": request.duration.strip().lower()
    }
    
    # JSON stable (clés triées) -> bytes -> hash
    json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()


def create_lesson(request: LessonRequest) -> Dict[str, str]:
    """
    Orchestre : génération -> persistance -> réponse.
    
    Returns:
        Dict avec lesson_id et title (pour réponse API)
        
    Raises:
        Exception: si génération ou persistance échouent
    """
    
    # 1. Calcul hash pour idempotence (optionnel en v0.1)
    request_hash = _compute_request_hash(request)
    
    # 2. Vérifier si déjà traité (idempotence basique)
    with get_session() as db:
        existing = db.query(Request).filter(Request.input_hash == request_hash).first()
        if existing and existing.lessons:
            # Retourner la leçon existante
            existing_lesson = existing.lessons[0]  # Première leçon associée
            return {
                "lesson_id": existing_lesson.id,
                "title": existing_lesson.title,
                "from_cache": True
            }
    
    # 3. Générer le contenu via l'agent
    lesson_content = generate_lesson(request)
    
    # 4. Persister Request + Lesson
    with get_session() as db:
        # Créer l'entrée Request
        db_request = Request(
            subject=request.subject,
            audience=request.audience, 
            duration=request.duration,
            input_hash=request_hash
        )
        db.add(db_request)
        db.flush()  # Pour avoir db_request.id
        
        # Créer l'entrée Lesson liée
        db_lesson = Lesson(
            request_id=db_request.id,
            title=lesson_content.title,
            content_md=lesson_content.content  # Le contenu principal
        )
        
        # Utiliser les propriétés JSON pour objectives/plan
        db_lesson.objectives = lesson_content.objectives
        db_lesson.plan = lesson_content.plan
        db_lesson.quiz = []  # Quiz vide pour v0.1 (ajouté plus tard)
        
        db.add(db_lesson)
        db.commit()
        
        return {
            "lesson_id": db_lesson.id,
            "title": db_lesson.title,
            "from_cache": False
        }


def get_lesson_by_id(lesson_id: str) -> Optional[Dict]:
    """
    Récupère une leçon par son ID.
    
    Returns:
        Dict avec toutes les données de la leçon, ou None si non trouvée
    """
    with get_session() as db:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            return None
            
        return {
            "id": lesson.id,
            "title": lesson.title,
            "content": lesson.content_md,
            "objectives": lesson.objectives,
            "plan": lesson.plan,
            "quiz": lesson.quiz,
            "created_at": lesson.created_at.isoformat()
        }