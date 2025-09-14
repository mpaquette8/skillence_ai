"""
Service d'orchestration SIMPLIFIÉ (sans quiz).

NETTOYAGE v0.1.2:
- Suppression de la logique quiz partout
- Focus sur génération + formatage + persistance de qualité
- Logs maintenus pour traçabilité
"""

# Inventaire des dépendances
# - hashlib (stdlib) : hash SHA-256 pour idempotence — éviter doublons
# - json (stdlib) : sérialisation stable pour hash — alternative: pickle mais moins portable
# - time (stdlib) : mesure des durées — nécessaire pour logs de performance
# - logging (stdlib) : warnings lisibilité — traçabilité
# - typing (stdlib) : annotations de types — améliore lisibilité
# - agents.lesson_generator (local) : DTOs + logique de génération — contenu principal
# - agents.formatter (local) : formatage Markdown — mise en forme
# - agents.quality_utils (local) : validation lisibilité — vérification audience
# - storage.base (local) : session DB — persistance
# - storage.models (local) : ORM Request/Lesson — modèles de données
# - api.middleware.logging (local) : helper de logs contextualisé — traçabilité
import hashlib
import json
import time
import logging
from typing import Dict, Optional, Any

from agents.lesson_generator import LessonRequest, LessonContent, generate_lesson
from agents.formatter import format_lesson
from agents.quality_utils import (
    validate_readability_for_audience,
    get_readability_summary,
)
from storage.base import get_session
from storage.models import Request, Lesson
from api.middleware.logging import log_operation, get_request_id

# Logger dédié à la lisibilité
logger = logging.getLogger("skillence_ai.readability")


def _compute_request_hash(request: LessonRequest) -> str:
    """Calcule un hash SHA-256 stable pour l'idempotence."""
    data = {
        "subject": request.subject.strip().lower(),
        "audience": request.audience.strip().lower(), 
        "duration": request.duration.strip().lower()
    }
    
    json_bytes = json.dumps(data, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(json_bytes).hexdigest()


def create_lesson(request: LessonRequest) -> Dict[str, Any]:
    """
    Orchestre génération + formatage + persistance (SANS QUIZ).
    Ajoute validation de lisibilité selon l'audience et retourne
    un dictionnaire avec métadonnées, métriques ``quality`` et ``tokens_used``.
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

            # Analyse lisibilité sur contenu en cache
            cached_score = validate_readability_for_audience(
                existing.lessons[0].content_md, request.audience
            )
            cached_summary = get_readability_summary(cached_score)
            if not cached_score.is_valid_for_audience:
                logger.warning(
                    f"[REQUEST {get_request_id()}] readability_warning - "
                    f"lesson_id={existing.lessons[0].id[:8]}, audience={request.audience}, "
                    f"score={cached_score.flesch_kincaid:.1f}"
                )

            # Résumé lisibilité exposé via "quality"
            return {
                "lesson_id": existing.lessons[0].id,
                "title": existing.lessons[0].title,
                "from_cache": True,
                "quality": {"readability": cached_summary},
                "tokens_used": 0,
            }

    # 2. Génération de contenu (focus qualité)
    generation_start = time.time()
    log_operation("agent_generation_started",
                  subject=request.subject, audience=request.audience)

    lesson_content, tokens_used = generate_lesson(request)
    formatted = format_lesson(lesson_content, request.audience)  # audience pour lisibilité

    # Validation lisibilité selon audience requête
    readability_score = validate_readability_for_audience(
        formatted.markdown, request.audience
    )
    readability_summary = get_readability_summary(readability_score)
    if not readability_score.is_valid_for_audience:
        logger.warning(
            f"[REQUEST {get_request_id()}] readability_warning - "
            f"audience={request.audience}, score={readability_score.flesch_kincaid:.1f}"
        )

    generation_duration = int((time.time() - generation_start) * 1000)
    log_operation(
        "agent_generation_completed",
        generation_duration,
        content_length=len(lesson_content.content),
        tokens_used=tokens_used,
    )

    # 3. Persistance en base (sans champs quiz)
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

        # Créer Lesson (sans quiz)
        db_lesson = Lesson(
            request_id=db_request.id,
            title=lesson_content.title,
            content_md=formatted.markdown
        )
        db_lesson.objectives = lesson_content.objectives
        db_lesson.plan = lesson_content.plan
        # SUPPRIMÉ: db_lesson.quiz

        db.add(db_lesson)
        db.commit()

        persistence_duration = int((time.time() - persistence_start) * 1000)
        total_duration = int((time.time() - start_time) * 1000)

        log_operation("lesson_persisted", persistence_duration,
                      lesson_id=db_lesson.id[:8])
        log_operation("lesson_creation_completed", total_duration,
                      from_cache=False)

        # Inclut les métriques de lisibilité dans "quality"
        return {
            "lesson_id": db_lesson.id,
            "title": db_lesson.title,
            "from_cache": False,
            "quality": {"readability": readability_summary},
            "tokens_used": tokens_used,
        }


def get_lesson_by_id(lesson_id: str) -> Optional[Dict]:
    """
    Récupère une leçon par ID (sans quiz) et résume sa lisibilité.
    """
    start_time = time.time()

    with get_session() as db:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        
        duration = int((time.time() - start_time) * 1000)
        
        if lesson:
            log_operation("lesson_retrieved", duration, lesson_id=lesson_id[:8])

            # Analyse lisibilité de la leçon récupérée
            readability_score = validate_readability_for_audience(
                lesson.content_md,
                lesson.request.audience,
            )
            readability_summary = get_readability_summary(readability_score)
            if not readability_score.is_valid_for_audience:
                logger.warning(
                    f"[REQUEST {get_request_id()}] readability_warning - "
                    f"lesson_id={lesson_id[:8]}, audience={lesson.request.audience}, "
                    f"score={readability_score.flesch_kincaid:.1f}"
                )

            formatted = {
                "id": lesson.id,
                "title": lesson.title,
                "content": lesson.content_md,
                "objectives": lesson.objectives,
                "plan": lesson.plan,
                # SUPPRIMÉ: "quiz": lesson.quiz,
                "created_at": lesson.created_at.isoformat(),
                "quality": {"readability": readability_summary},
            }
            return formatted
        else:
            log_operation("lesson_not_found", duration, lesson_id=lesson_id[:8])
            return None
