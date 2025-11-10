# // file: agents/lesson_generator.py

"""
Agent 'lesson_generator' avec BUDGET TOKENS strict (v0.1.3).

AJOUT v0.1.3:
- Validation budget 2000 tokens AVANT appel OpenAI
- Contrôle coûts + prevention timeouts
- Messages d'erreur pédagogiques pour l'utilisateur

Contraintes MVP :
- Python 3.11+, Pydantic v2
- BUDGET STRICT: 1800 tokens prompt + 200 tokens réponse = 2000 total
- Timeout 15s maintenu
"""

# Inventaire des dépendances
# - typing (stdlib) : types statiques (List, Literal, Tuple) — Tuple pour retour multiple
# - time (stdlib) : pause avant retry en cas d'erreurs transitoires — alternative: asyncio.sleep mais impose async
# - json (stdlib) : parse la réponse OpenAI — alternative: eval() mais dangereux
# - fastapi (tierce) : HTTPException pour les erreurs API — standard FastAPI
# - openai (tierce) : client OpenAI officiel — alternative: requests mais moins pratique
# - pydantic (tierce) : BaseModel/Field pour validation v2 ; field_validator pour nettoyer le sujet
# - .token_utils (local) : validation budget — contrôle coûts MVP critique
from typing import List, Literal, Tuple
import time
import json

from fastapi import HTTPException
from openai import OpenAI
from pydantic import BaseModel, Field, field_validator
from storage.base import settings
from .token_utils import validate_prompt_budget

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

    @field_validator("subject")
    @classmethod
    def normalize_subject(cls, value: str) -> str:
        """Nettoie le sujet pour éviter les espaces/retours à la ligne superflus."""
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Le sujet doit contenir au moins 2 caractères significatifs")
        return normalized


class LessonContent(BaseModel):
    """Sortie du générateur (plan + contenu explicatif de qualité)."""
    title: str
    objectives: List[str]
    plan: List[str] 
    content: str


def generate_lesson(request: LessonRequest) -> Tuple[LessonContent, int]:
    """
    Génère une leçon de qualité via l'API OpenAI avec CONTRÔLE BUDGET.

    NOUVEAU v0.1.3: Validation stricte 1800 tokens prompt avant appel API.
    Retourne également le nombre total de tokens consommés.
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
    
    # NOUVEAU: Validation budget AVANT appel OpenAI (évite coûts + timeouts)
    validate_prompt_budget(prompt, {
        "subject": request.subject,
        "audience": request.audience,
        "duration": request.duration
    })
    
    def _call_openai(max_tokens: int) -> Tuple[str, int]:
        """Encapsule l'appel OpenAI en gérant les erreurs transitoires."""
        for attempt in range(2):
            try:
                resp_inner = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=max_tokens,
                    temperature=0.3
                )
                total = getattr(getattr(resp_inner, "usage", None), "total_tokens", 0) or 0
                content_inner = resp_inner.choices[0].message.content
                if not content_inner or content_inner.strip() == "":
                    raise HTTPException(
                        status_code=500,
                        detail="OpenAI a retourné une réponse vide"
                    )
                return content_inner, total
            except Exception as exc:
                error_msg = str(exc).lower()
                transient = any(
                    key in error_msg for key in ("timeout", "timed out", "rate limit", "429")
                )
                if attempt == 0 and transient:
                    time.sleep(2)
                    continue

                if "timeout" in error_msg or "timed out" in error_msg:
                    raise HTTPException(
                        status_code=504,
                        detail=f"Timeout OpenAI ({settings.OPENAI_TIMEOUT}s) - Réessayez dans quelques secondes"
                    ) from exc
                if "rate limit" in error_msg or "429" in error_msg:
                    raise HTTPException(
                        status_code=429,
                        detail="Limite de taux OpenAI atteinte - Réessayez dans 1 minute"
                    ) from exc
                if "quota" in error_msg or "402" in error_msg:
                    raise HTTPException(
                        status_code=402,
                        detail="Quota OpenAI épuisé - Vérifiez votre compte sur platform.openai.com"
                    ) from exc
                if "authentication" in error_msg or "401" in error_msg:
                    raise HTTPException(
                        status_code=401,
                        detail="Clé OpenAI invalide - Vérifiez OPENAI_API_KEY dans .env"
                    ) from exc

                raise HTTPException(
                    status_code=500,
                    detail=f"Erreur OpenAI: {str(exc)[:100]}"
                ) from exc

        raise HTTPException(status_code=500, detail="Appel OpenAI impossible après retries")

    content: str = ""
    total_tokens: int = 0
    max_tokens_candidates = [200, 320]
    last_error: Optional[json.JSONDecodeError] = None

    for max_tokens in max_tokens_candidates:
        content, total_tokens = _call_openai(max_tokens)

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            last_error = exc
            # Tentative suivante avec plus de tokens
            continue

        # Validation des champs requis
        required_fields = ["title", "objectives", "plan", "content"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            raise HTTPException(
                status_code=500,
                detail=f"OpenAI n'a pas fourni les champs requis: {', '.join(missing_fields)}"
            )

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

        try:
            return LessonContent(**data), total_tokens
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur de construction LessonContent: {str(exc)[:100]}"
            ) from exc

    if last_error:
        raise HTTPException(
            status_code=500,
            detail=f"OpenAI a retourné un JSON invalide: {str(last_error)[:100]}\n"
                   f"Contenu reçu: {content[:200]}..."
        ) from last_error

    raise HTTPException(status_code=500, detail="Échec de parsing JSON sans erreur explicite")

    # Construction du modèle validé
    try:
        return LessonContent(**data), total_tokens

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur de construction LessonContent: {str(exc)[:100]}"
        ) from exc
