# // file: skillence_ai/agents/lesson_generator.py

"""
Agent 'lesson_generator' (stub) — Pydantic partout.

Rôle:
- Définir les modèles d'entrée/sortie (Pydantic v2) pour la génération de leçon.
- Fournir une fonction `generate_lesson` qui produit un plan + contenu (mock).
- Servira d'interface stable avant intégration LLM (Semaine 2 : tool calling).

Contraintes:
- Python 3.11+, Pydantic v2.
- Pas d'appel externe ici (pas de secrets).
"""

# Inventaire des dépendances
# - typing (stdlib) : types statiques (List) — alternative: collections.abc pour Sequence
# - pydantic (tierce) : modèles de validation/sérialisation (BaseModel v2)
from typing import List  # stdlib — typing statique pour les listes
from pydantic import BaseModel, Field  # tierce — data models/validation (vs dataclasses sans validation)


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
    """
    Génère une leçon vulgarisée (stub synchrone).
    Remplacé plus tard par un appel LLM avec timeouts et limites de tokens.
    """
    # NB: on adapte légèrement selon la durée pour montrer la future variabilité
    if request.duration == "short":
        plan = ["Introduction", "Points clés", "Conclusion"]
        words_hint = "~300 mots"
    elif request.duration == "medium":
        plan = ["Introduction", "Développement", "Exemples", "Conclusion"]
        words_hint = "~600 mots"
    else:
        plan = ["Introduction", "Contexte", "Développement", "Études de cas", "Conclusion"]
        words_hint = "~900 mots"

    return LessonContent(
        title=f"{request.subject} (niveau {request.audience})",
        objectives=[
            "Comprendre les bases du sujet",
            "Identifier les étapes clés",
        ],
        plan=plan,
        content=(
            f"Explication vulgarisée de {request.subject}, adaptée pour un public {request.audience}. "
            f"Cette version {request.duration} vise {words_hint} et reste factuellement simple (MVP)."
        ),
    )
