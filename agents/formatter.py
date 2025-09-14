"""
Agent `formatter` — mise en forme Markdown SIMPLIFIÉ (SANS QUIZ).

NETTOYAGE v0.1.2:
- Suppression complète de la logique quiz
- Focus sur un Markdown pédagogique de qualité
- Structure claire et exportable
"""

# Inventaire des dépendances
# - pydantic (tierce) : modèles de validation v2 — BaseModel pour structure
# - agents.lesson_generator (local) : DTO d'entrée LessonContent — contenu à formater
# - agents.quality_utils (local) : validation et résumé lisibilité
from pydantic import BaseModel
from .lesson_generator import LessonContent
from .quality_utils import (
    validate_readability_for_audience,
    get_readability_summary,
)


class LessonFormatted(BaseModel):
    """Résultat final du formatter (SIMPLIFIÉ - sans quiz)."""
    title: str
    markdown: str
    readability: dict
    # SUPPRIMÉ: quiz field


def _build_markdown(content: LessonContent) -> str:
    """Assemble un Markdown pédagogique de qualité."""
    lines = [f"# {content.title}", ""]

    # Objectifs d'apprentissage
    lines.append("## Objectifs d'apprentissage")
    for obj in content.objectives:
        lines.append(f"- {obj}")
    lines.append("")

    # Plan de la leçon
    lines.append("## Plan de la leçon")
    for i, step in enumerate(content.plan, 1):
        lines.append(f"{i}. {step}")
    lines.append("")

    # Contenu principal (développement)
    lines.append("## Contenu")
    lines.append(content.content)
    lines.append("")

    return "\n".join(lines)


def format_lesson(content: LessonContent, audience: str) -> LessonFormatted:
    """
    Construit un Markdown pédagogique structuré (FOCUS v0.1).

    Args:
        content: Contenu généré par lesson_generator
        audience: Public cible servant à évaluer la lisibilité

    Returns:
        Markdown formaté prêt à l'export
    """
    markdown = _build_markdown(content)

    # Analyse de lisibilité adaptée à l'audience fournie
    score = validate_readability_for_audience(markdown, audience)
    readability = get_readability_summary(score)

    return LessonFormatted(
        title=content.title,
        markdown=markdown,
        readability=readability,
    )
