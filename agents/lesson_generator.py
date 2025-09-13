# // file: skillence_ai/agents/lesson_generator.py

"""
Agent 'lesson_generator' — génération via API OpenAI.

Rôle:
- Définir les modèles d'entrée/sortie (Pydantic v2) pour la génération de leçon.
- Fournir une fonction `generate_lesson` qui s'appuie sur OpenAI Chat Completions.

Contraintes:
- Python 3.11+, Pydantic v2.
- Appel externe avec timeout et limite de tokens.
"""

# Inventaire des dépendances
# - typing (stdlib) : types statiques (List)
# - json (stdlib)   : parse la réponse OpenAI
# - httpx (tierce)  : timeout pour l'appel OpenAI
# - fastapi (tierce) : HTTPException pour les erreurs API
# - openai (tierce) : client OpenAI 2025
# - pydantic (tierce) : modèles de validation
from typing import List
import json

import httpx
from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from storage.base import settings

client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=httpx.Timeout(15.0))


class LessonRequest(BaseModel):
    """Entrée de génération de leçon (validée par Pydantic)."""
    subject: str = Field(..., min_length=2, max_length=200, description="Sujet de la leçon")
    audience: str = Field(..., min_length=2, max_length=50, description="Ex: enfant, lycéen, adulte")
    duration: str = Field(..., pattern="^(short|medium|long)$", description="Granularité de la leçon")


class LessonContent(BaseModel):
    """Sortie du générateur (plan + texte)."""
    title: str
    objectives: List[str]
    plan: List[str]
    content: str


def generate_lesson(request: LessonRequest) -> LessonContent:
    """Génère une leçon via l'API OpenAI."""
    prompt = (
        "Tu es un assistant pédagogique. Réponds avec un JSON contenant les clés "
        "'title', 'objectives', 'plan', 'content'.\n"
        f"Sujet: {request.subject}\nAudience: {request.audience}\nDurée: {request.duration}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail="OpenAI API call failed") from exc

    try:
        data = json.loads(resp.choices[0].message.content)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Invalid OpenAI response") from exc

    return LessonContent(**data)
