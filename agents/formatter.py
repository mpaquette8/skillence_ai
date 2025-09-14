# // file: agents/formatter.py
"""
Agent `formatter` — mise en forme locale.
Transforme `LessonContent` en Markdown + quiz déterministe (pas d’appel réseau).
"""

# Inventaire des dépendances
# - typing (stdlib)      : annotations (List, Dict) — alternative: collections.abc
# - random (stdlib)      : tirer une bonne réponse aléatoire — alternative: secrets (inutile ici)
# - pydantic (tierce)    : modèles de validation (BaseModel v2)
# - agents.lesson_generator (local) : DTO d’entrée (LessonContent)

from typing import List, Dict            # stdlib — types structurants
import random                           # stdlib — choisir la bonne option de quiz
from pydantic import BaseModel, Field   # tierce — modèles/validation
from .lesson_generator import LessonContent  # local — contenu brut à formater


class QuizItem(BaseModel):
    """Question QCM minimaliste."""
    question: str
    options: List[str]
    answer_index: int = Field(ge=0, lt=4)


class LessonFormatted(BaseModel):
    """Résultat final du formatter."""
    title: str
    markdown: str
    quiz: List[QuizItem]


def _build_markdown(content: LessonContent) -> str:
    """Assemble un Markdown simple à partir du contenu généré."""
    lines = [f"# {content.title}", ""]

    lines.append("## Objectifs")
    for obj in content.objectives:
        lines.append(f"- {obj}")
    lines.append("")

    lines.append("## Plan")
    for step in content.plan:
        lines.append(f"- {step}")
    lines.append("")

    lines.append("## Contenu")
    lines.append(content.content)
    lines.append("")

    return "\n".join(lines)


def _generate_quiz(content: LessonContent) -> List[QuizItem]:
    """Crée 5 questions factices à partir du sujet."""
    quiz: List[QuizItem] = []
    for i in range(1, 6):
        options = [f"Option {j}" for j in range(1, 5)]
        answer = random.randrange(0, 4)
        quiz.append(
            QuizItem(
                question=f"Question {i} sur {content.title} ?",
                options=options,
                answer_index=answer,
            )
        )
    return quiz


def format_lesson(content: LessonContent, include_quiz: bool = True) -> LessonFormatted:
    """
    Construit le Markdown final et un quiz optionnel.
    
    Args:
        content: Contenu généré par lesson_generator
        include_quiz: Si False, retourne quiz vide []
    """
    markdown = _build_markdown(content)
    
    # Quiz conditionnel
    if include_quiz:
        quiz = _generate_quiz(content)
    else:
        quiz = []  # Quiz vide si pas demandé
    
    return LessonFormatted(
        title=content.title, 
        markdown=markdown, 
        quiz=quiz
    )
