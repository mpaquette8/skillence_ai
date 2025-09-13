# // file: api/main.py

"""
Application FastAPI complète (MVP v0.1).
Expose:
- GET /v1/health : ping
- POST /v1/lessons : génère une leçon + persiste en base
- GET /v1/lessons/{id} : récupère une leçon existante

Contraintes:
- Pydantic v2 pour I/O
- Initialisation automatique de la base SQLite
- Service d'orchestration pour découpler logique métier
"""

# Inventaire des dépendances
# - fastapi (tierce) : framework ASGI + HTTPException — alternative: Starlette mais moins d'outils
# - pydantic (tierce) : modèles de réponse API — validation automatique des entrées/sorties
# - typing (stdlib) : annotations de types (Dict, Optional)
# - agents.lesson_generator (local) : DTO d'entrée LessonRequest
# - api.services.lessons (local) : orchestration create_lesson + get_lesson_by_id
# - storage.base (local) : init_db pour créer les tables au démarrage
from fastapi import FastAPI, HTTPException  # tierce — serveur web + gestion d'erreurs
from pydantic import BaseModel  # tierce — modèle de réponse
from typing import Dict, Optional  # stdlib — typing

from agents.lesson_generator import LessonRequest  # local — DTO d'entrée
from api.services.lessons import create_lesson, get_lesson_by_id  # local — orchestration
from storage.base import init_db  # local — initialisation DB


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


# Application FastAPI
app = FastAPI(
    title="Skillence AI — MVP", 
    version="0.1.0",
    description="API de génération de leçons pédagogiques vulgarisées"
)


@app.on_event("startup")
def startup_event() -> None:
    """
    Initialise la base de données au démarrage.
    Crée les tables SQLite si elles n'existent pas.
    """
    init_db()


@app.get("/v1/health")
def health() -> Dict[str, str]:
    """Vérification simple de vivacité."""
    return {"status": "ok"}


@app.post("/v1/lessons", response_model=LessonResponse)
def create_lesson_endpoint(payload: LessonRequest) -> LessonResponse:
    """
    Crée une leçon (plan + contenu) à partir d'un sujet/audience/durée.
    
    - Génère le contenu via l'agent lesson_generator
    - Persiste en base SQLite (tables requests + lessons)
    - Gère l'idempotence basique (même input = même résultat)
    
    Returns:
        LessonResponse avec lesson_id pour récupération ultérieure
        
    Raises:
        HTTPException 400: si validation Pydantic échoue
        HTTPException 500: si génération ou persistance échouent
    """
    try:
        # Validation déjà assurée par Pydantic via `payload`
        result = create_lesson(payload)
        
        return LessonResponse(
            lesson_id=result["lesson_id"],
            title=result["title"],
            message="Leçon générée avec succès",
            from_cache=result.get("from_cache", False)
        )
        
    except Exception as exc:
        # En MVP : erreur 500 simple avec message (plus tard: logs structurés + run_id)
        raise HTTPException(
            status_code=500, 
            detail=f"Échec de génération de leçon: {str(exc)}"
        ) from exc


@app.get("/v1/lessons/{lesson_id}", response_model=LessonDetailResponse)
def get_lesson_endpoint(lesson_id: str) -> LessonDetailResponse:
    """
    Récupère une leçon existante par son ID.
    
    Args:
        lesson_id: UUID de la leçon (généré lors de la création)
        
    Returns:
        LessonDetailResponse avec contenu complet (markdown + métadonnées)
        
    Raises:
        HTTPException 404: si lesson_id n'existe pas
        HTTPException 500: si erreur de base de données
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
        # Re-raise les HTTPException (404) sans les wrapper
        raise
    except Exception as exc:
        # Erreurs inattendues (DB, etc.)
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération: {str(exc)}"
        ) from exc