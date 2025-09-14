"""
Application FastAPI SIMPLIFIÉE (sans quiz) avec logs (MVP v0.1.2).

NETTOYAGE v0.1.2:
- Suppression des références quiz dans les réponses API
- Focus sur le contenu pédagogique de qualité
- Middleware de logging maintenu
"""

# Inventaire des dépendances
# - logging (stdlib) : configuration des logs — système de logging
# - fastapi (tierce) : framework ASGI + HTTPException — serveur principal
# - pydantic (tierce) : modèles de réponse API — validation I/O
# - typing (stdlib) : annotations de types — améliore lisibilité
# - agents.lesson_generator (local) : DTO d'entrée — modèle de requête
# - api.services.lessons (local) : orchestration métier — logique principale
# - api.middleware.logging (local) : middleware de logs — corrélation requêtes
# - storage.base (local) : initialisation DB — setup base de données
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, Any

from agents.lesson_generator import LessonRequest
from api.services.lessons import create_lesson, get_lesson_by_id
from api.middleware.logging import LoggingMiddleware
from storage.base import init_db

# Configuration des logs (format simple pour MVP)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("skillence_ai.main")


# Modèles de réponse API (SANS QUIZ)
class LessonResponse(BaseModel):
    """Réponse POST /v1/lessons (création) - SIMPLIFIÉ.

    Inclut les métriques de qualité (ex: lisibilité) sous ``quality``
    ainsi que les ``tokens_used``.
    """
    lesson_id: str
    title: str
    message: str
    quality: Dict[str, Any]
    tokens_used: int
    from_cache: Optional[bool] = False


class LessonDetailResponse(BaseModel):
    """Réponse GET /v1/lessons/{id} (détail complet) avec métriques."""
    id: str
    title: str
    content: str
    objectives: list[str]
    plan: list[str]
    # SUPPRIMÉ: quiz: list[dict]
    created_at: str
    quality: Dict[str, Any]


# Application FastAPI avec middleware de logs
app = FastAPI(
    title="Skillence AI — MVP v0.1.2", 
    version="0.1.2",
    description="API de génération de leçons pédagogiques vulgarisées (sans quiz)"
)

# Ajouter le middleware de logging
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
def startup_event() -> None:
    """Initialise l'application au démarrage."""
    logger.info("Skillence AI v0.1.2 starting up (focus: contenu de qualité)...")
    init_db()
    logger.info("Database initialized - ready to serve requests")


@app.get("/v1/health")
def health() -> Dict[str, str]:
    """Vérification simple de vivacité."""
    return {"status": "ok"}


@app.post("/v1/lessons", response_model=LessonResponse)
def create_lesson_endpoint(payload: LessonRequest) -> LessonResponse:
    """
    Crée une leçon pédagogique de qualité (plan + contenu vulgarisé).
    Retourne les métadonnées de leçon et un résumé ``quality`` (ex: lisibilité).
    """
    try:
        result = create_lesson(payload)

        return LessonResponse(
            lesson_id=result["lesson_id"],
            title=result["title"],
            message="Leçon pédagogique générée avec succès",
            quality=result["quality"],
             tokens_used=result["tokens_used"],
            from_cache=result.get("from_cache", False),
        )
        
    except Exception as exc:
        logger.error(f"Lesson creation failed: {str(exc)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Échec de génération de leçon: {str(exc)}"
        ) from exc


@app.get("/v1/lessons/{lesson_id}", response_model=LessonDetailResponse)
def get_lesson_endpoint(lesson_id: str) -> LessonDetailResponse:
    """
    Récupère une leçon existante par son ID (contenu, métadonnées et métriques).
    """
    try:
        lesson_data = get_lesson_by_id(lesson_id)
        
        if not lesson_data:
            raise HTTPException(
                status_code=404,
                detail=f"Leçon {lesson_id} non trouvée"
            )
        
        return LessonDetailResponse(**lesson_data)
        
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Lesson retrieval failed for {lesson_id}: {str(exc)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(exc)}"
        ) from exc
