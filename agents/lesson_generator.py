# // file: agents/lesson_generator.py

"""
Agent 'lesson_generator' — génération via API OpenAI (NETTOYÉ v0.1.2).

NETTOYAGE v0.1.2:
- Suppression complète du quiz (reporté v0.2)  
- Focus sur l'excellence du contenu explicatif
- Simplification du modèle LessonRequest

Contraintes MVP :
- Python 3.11+, Pydantic v2.
- Max 2000 tokens, timeout 15s.
"""

# Inventaire des dépendances
# - typing (stdlib) : types statiques (List, Literal) — Literal pour enum strictes
# - json (stdlib) : parse la réponse OpenAI — alternative: eval() mais dangereux
# - fastapi (tierce) : HTTPException pour les erreurs API — standard FastAPI
# - openai (tierce) : client OpenAI officiel — alternative: requests mais moins pratique
# - pydantic (tierce) : modèles de validation v2 — alternative: dataclasses mais validation manuelle
from typing import List, Literal
import json

from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field
from storage.base import settings

# Client OpenAI avec timeout configuré
client = OpenAI(
    api_key=settings.OPENAI_API_KEY, 
    timeout=float(settings.OPENAI_TIMEOUT)
)


class LessonRequest(BaseModel):
    """Entrée de génération de leçon (SIMPLIFIÉ - sans quiz)."""
    subject: str = Field(..., min_length=2, max_length=200, description="Sujet de la leçon")
    
    audience: Literal["enfant", "lycéen", "adulte"] = Field(
        ..., description="Niveau de l'audience cible"
    )
    duration: Literal["short", "medium", "long"] = Field(
        ..., description="Durée souhaitée de la leçon"
    )
    
    # SUPPRIMÉ: include_quiz (reporté v0.2)


class LessonContent(BaseModel):
    """Sortie du générateur (plan + contenu explicatif de qualité)."""
    title: str
    objectives: List[str]
    plan: List[str] 
    content: str


def generate_lesson(request: LessonRequest) -> LessonContent:
    """
    Génère une leçon de qualité via l'API OpenAI.
    
    Focus v0.1: Excellence du contenu explicatif (sans quiz).
    """
    # Construction du prompt focalisé sur la qualité explicative
    prompt = (
        "Tu es un assistant pédagogique expert. Tu dois répondre UNIQUEMENT avec un JSON valide "
        "contenant exactement ces 4 clés : 'title', 'objectives', 'plan', 'content'.\n\n"
        "FOCUS: Contenu explicatif de qualité avec analogies et exemples concrets.\n\n"
        f"Sujet: {request.subject}\n"
        f"Audience: {request.audience}\n"  
        f"Durée: {request.duration}\n\n"
        "Format attendu:\n"
        "{\n"
        '  "title": "Titre adapté au niveau",\n'
        '  "objectives": ["Objectif pédagogique 1", "Objectif 2"],\n'
        '  "plan": ["Section 1", "Section 2", "Section 3"],\n'
        '  "content": "Contenu vulgarisé avec analogies et exemples"\n'
        "}"
    )
    
    # Appel OpenAI avec gestion d'erreurs spécifiques
    try:
        resp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,  # Limite MVP respectée
            temperature=0.3
        )
        
    except Exception as exc:
        error_msg = str(exc).lower()
        
        if "timeout" in error_msg or "timed out" in error_msg:
            raise HTTPException(
                status_code=504, 
                detail=f"Timeout OpenAI ({settings.OPENAI_TIMEOUT}s) - Réessayez dans quelques secondes"
            ) from exc
        
        elif "rate limit" in error_msg or "429" in error_msg:
            raise HTTPException(
                status_code=429,
                detail="Limite de taux OpenAI atteinte - Réessayez dans 1 minute"
            ) from exc
            
        elif "quota" in error_msg or "402" in error_msg:
            raise HTTPException(
                status_code=402, 
                detail="Quota OpenAI épuisé - Vérifiez votre compte sur platform.openai.com"
            ) from exc
            
        elif "authentication" in error_msg or "401" in error_msg:
            raise HTTPException(
                status_code=401,
                detail="Clé OpenAI invalide - Vérifiez OPENAI_API_KEY dans .env"
            ) from exc
        
        # Erreur générique
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur OpenAI: {str(exc)[:100]}"
        ) from exc

    # Extraction et validation de la réponse
    try:
        content = resp.choices[0].message.content
        if not content or content.strip() == "":
            raise HTTPException(
                status_code=500,
                detail="OpenAI a retourné une réponse vide"
            )
            
    except (IndexError, AttributeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Format de réponse OpenAI inattendu"
        ) from exc

    # Parsing JSON unique avec validation
    try:
        data = json.loads(content)
        
        # Validation des champs requis
        required_fields = ["title", "objectives", "plan", "content"]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI n'a pas fourni les champs requis: {', '.join(missing_fields)}"
            )
        
        # Validation des types
        if not isinstance(data.get("objectives"), list):
            raise HTTPException(
                status_code=500, 
                detail="Le champ 'objectives' doit être une liste"
            )
            
        if not isinstance(data.get("plan"), list):
            raise HTTPException(
                status_code=500,
                detail="Le champ 'plan' doit être une liste"
            )
            
        # Validation du contenu minimum
        if len(data["objectives"]) < 1:
            raise HTTPException(
                status_code=500,
                detail="Au moins un objectif est requis"
            )
            
        if len(data["plan"]) < 2:
            raise HTTPException(
                status_code=500, 
                detail="Au moins 2 sections sont requises dans le plan"
            )
        
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI a retourné un JSON invalide: {str(exc)[:100]}\n"
                   f"Contenu reçu: {content[:200]}..."
        ) from exc
    
    except HTTPException:
        raise
        
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de validation de la réponse OpenAI: {str(exc)[:100]}"
        ) from exc

    # Construction du modèle validé
    try:
        return LessonContent(**data)
        
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de construction LessonContent: {str(exc)[:100]}"
        ) from exc