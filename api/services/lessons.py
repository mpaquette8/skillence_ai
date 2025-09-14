# // file: api/services/lessons.py

"""
Service d'orchestration avec logs intégrés.
Trace les opérations agent + persistance pour debugging et monitoring.
"""

# Inventaire des dépendances
# - hashlib (stdlib) : hash SHA-256 pour idempotence 
# - json (stdlib) : sérialisation stable pour hash
# - time (stdlib) : mesure des durées — nécessaire pour logs de performance
# - typing (stdlib) : annotations de types
# - agents.lesson_generator (local) : DTOs + logique de génération
# - storage.base (local) : session DB
# - storage.models (local) : ORM Request/Lesson  
# - api.middleware.logging (local) : helper de logs contextualisé
import hashlib
import json
import time  # stdlib — timing pour logs
from typing import Dict, Optional

from agents.lesson_generator import LessonRequest, LessonContent, generate_lesson
from agents.formatter import format_lesson
from storage.base import get_session
from storage.models import Request, Lesson
from api.middleware.logging import log_operation  # local — logs avec request_id


def _compute_request_hash(request: LessonRequest) -> str:
    """Calcule un hash SHA-256 stable pour l'idempotence."""
    data = {
        "subject": request.subject.strip().lower(),
        "audience": request.audience.strip().lower(), 
        "duration": request.duration.strip().lower()
    }
    
    json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()


def create_lesson(request: LessonRequest) -> Dict[str, str]:
    """
    Orchestre génération + persistance avec logs détaillés.
    """
    start_time = time.time()
    
    # 1. Calcul hash + vérification cache
    request_hash = _compute_request_hash(request)
    log_operation("idempotence_check", hash=request_hash[:8])
    
    with get_session() as db:
        existing = db.query(Request).filter(Request.input_hash == request_hash).first()
        if existing and existing.lessons:
            cache_duration = int((time.time() - start_time) * 1000)
            log_operation("lesson_from_cache", cache_duration, 
                         lesson_id=existing.lessons[0].id[:8])
            return {
                "lesson_id": existing.lessons[0].id,
                "title": existing.lessons[0].title,
                "from_cache": True
            }
    
    # 2. Génération de contenu
    generation_start = time.time()
    log_operation("agent_generation_started", 
                  subject=request.subject, audience=request.audience)
    
    lesson_content = generate_lesson(request)
    formatted = format_lesson(lesson_content, include_quiz=request.include_quiz)
    
    generation_duration = int((time.time() - generation_start) * 1000)
    log_operation("agent_generation_completed", generation_duration,
                  content_length=len(lesson_content.content))
    
    # 3. Persistance en base
    persistence_start = time.time()
    
    with get_session() as db:
        # Créer Request
        db_request = Request(
            subject=request.subject,
            audience=request.audience, 
            duration=request.duration,
            input_hash=request_hash
        )
        db.add(db_request)
        db.flush()
        
        # Créer Lesson
        db_lesson = Lesson(
            request_id=db_request.id,
            title=lesson_content.title,
            content_md=formatted.markdown
        )
        db_lesson.objectives = lesson_content.objectives
        db_lesson.plan = lesson_content.plan
        db_lesson.quiz = [q.model_dump() for q in formatted.quiz]
        
        db.add(db_lesson)
        db.commit()
        
        persistence_duration = int((time.time() - persistence_start) * 1000)
        total_duration = int((time.time() - start_time) * 1000)
        
        log_operation("lesson_persisted", persistence_duration,
                      lesson_id=db_lesson.id[:8])
        log_operation("lesson_creation_completed", total_duration,
                      from_cache=False)
        
        return {
            "lesson_id": db_lesson.id,
            "title": db_lesson.title,
            "from_cache": False
        }


def get_lesson_by_id(lesson_id: str) -> Optional[Dict]:
    """
    Récupère une leçon avec log simple.
    """
    start_time = time.time()
    
    with get_session() as db:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        duration = int((time.time() - start_time) * 1000)
        
        if lesson:
            log_operation("lesson_retrieved", duration, lesson_id=lesson_id[:8])
            formatted = {
                "id": lesson.id,
                "title": lesson.title,
                "content": lesson.content_md,
                "objectives": lesson.objectives,
                "plan": lesson.plan,
                "quiz": lesson.quiz,
                "created_at": lesson.created_at.isoformat()
            }
            return formatted
        else:
            log_operation("lesson_not_found", duration, lesson_id=lesson_id[:8])
            return None
