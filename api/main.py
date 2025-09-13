# // file: api/main.py

"""
Application FastAPI complète avec système de logs (MVP v0.1).
Intègre le middleware de correlation ID pour traçabilité.
"""

# Inventaire des dépendances
# - fastapi (tierce) : framework ASGI + HTTPException — serveur principal
# - pydantic (tierce) : modèles de réponse API — validation I/O
# - typing (stdlib) : annotations de types — améliore lisibilité
# - logging (stdlib) : configuration des logs — système de logging
# - agents.lesson_generator (local) : DTO d'entrée — modèle de requête
# - api.services.lessons (local) : orchestration métier — logique principale  
# - api.middleware.logging (local) : middleware de logs — corrélation requêtes
# - storage.base (local) : initialisation DB — setup base de données
import logging  # stdlib — configuration logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional

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

# Logger pour l'application principale
logger = logging.getLogger("skillence_ai.main")


# Modèles de réponse API (Pydantic v2)
class LessonResponse(BaseModel):
    """Réponse POST /v1/lessons (création)."""
    lesson_id: str
    title: str
    message: str
    from_cache: Optional[bool] = False


class LessonDetailResponse(BaseModel):
    """Réponse GET /v1/lessons/{id} (détail complet)."""
    id: str
    title: str
    content: str
    objectives: list[str]
    plan: list[str]
    quiz: list[dict]
    created_at: str


# Application FastAPI avec middleware de logs
app = FastAPI(
    title="Skillence AI — MVP", 
    version="0.1.0",
    description="API de génération de leçons pédagogiques vulgarisées"
)

# Ajouter le middleware de logging (important: avant les routes)
app.add_middleware(LoggingMiddleware)


@app.on_event("startup")
def startup_event() -> None:
    """
    Initialise l'application au démarrage.
    Logs + DB initialization.
    """
    logger.info("Skillence AI starting up...")
    init_db()
    logger.info("Database initialized - ready to serve requests")


@app.get("/v1/health")
def health() -> Dict[str, str]:
    """Vérification simple de vivacité."""
    return {"status": "ok"}


@app.post("/v1/lessons", response_model=LessonResponse)
def create_lesson_endpoint(payload: LessonRequest) -> LessonResponse:
    """
    Crée une leçon (plan + contenu) à partir d'un sujet/audience/durée.
    Logs intégrés pour traçabilité complète du processus.
    """
    try:
        result = create_lesson(payload)
        
        return LessonResponse(
            lesson_id=result["lesson_id"],
            title=result["title"],
            message="Leçon générée avec succès",
            from_cache=result.get("from_cache", False)
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
    Récupère une leçon existante par son ID.
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