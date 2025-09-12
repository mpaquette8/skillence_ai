# // file: skillence_ai/api/main.py

"""
Application FastAPI minimale (MVP Semaine 1).
Expose:
- GET /v1/health : ping
- POST /v1/lessons : génère une leçon via l'agent 'lesson_generator'

Contraintes:
- Pydantic v2 pour I/O.
- Pas de DB dans cet incrément (test e2e avec stub).
"""

# Inventaire des dépendances
# - fastapi (tierce) : framework ASGI pour routes HTTP — alternative: Starlette (plus bas niveau)
# - pydantic (tierce) : pour types de réponse si besoin — ici surtout importé via l'agent
# - typing (stdlib) : annotations de types (NoReturn, Optional, etc.) — ici non requis
# - skillence_ai.agents.lesson_generator (local) : logique de génération (stub)
from fastapi import FastAPI, HTTPException  # tierce — serveur web; HTTPException pour erreurs cadrées
from agents.lesson_generator import (  # local — nos DTOs + service
    LessonRequest,
    LessonContent,
    generate_lesson,
)

app = FastAPI(title="Skillence AI — MVP", version="0.1.0")


@app.get("/v1/health")
def health() -> dict:
    """Vérification simple de vivacité."""
    return {"status": "ok"}


@app.post("/v1/lessons", response_model=LessonContent)
def create_lesson(payload: LessonRequest) -> LessonContent:
    """
    Crée une leçon (plan + contenu) à partir d'un sujet/audience/durée.
    Pour l'instant, s'appuie sur un stub synchrone.
    """
    try:
        # Validation déjà assurée par Pydantic via `payload`.
        result = generate_lesson(payload)
        return result
    except Exception as exc:
        # En MVP: on renvoie une erreur 500 simple. (Plus tard: logs structurés + run_id)
        raise HTTPException(status_code=500, detail=f"Lesson generation failed: {exc}")  # noqa: B904
