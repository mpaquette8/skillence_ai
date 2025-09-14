"""
Tests unitaires formatter CORRIGÉS (sans quiz) - v0.1.2.

NETTOYAGE:
- Suppression de toutes les vérifications quiz
- Focus sur la qualité du Markdown structuré
"""

# Inventaire des dépendances
# - agents.lesson_generator (local) : LessonContent DTO — contenu d'entrée
# - agents.formatter (local) : format_lesson function — fonction à tester
from agents.lesson_generator import LessonContent
from agents.formatter import format_lesson


def test_format_lesson_creates_structured_markdown():
    """
    Test que le formatter produit un Markdown bien structuré (SANS QUIZ).
    """
    content = LessonContent(
        title="La photosynthèse expliquée",
        objectives=["Comprendre le processus", "Identifier les étapes"],
        plan=["Introduction", "Le processus", "Importance écologique"],
        content="La photosynthèse est un processus vital...",
    )

    formatted = format_lesson(content)

    # Vérifications structure Markdown
    assert formatted.markdown.startswith("# La photosynthèse expliquée")
    assert "## Objectifs d'apprentissage" in formatted.markdown
    assert "## Plan de la leçon" in formatted.markdown
    assert "## Contenu" in formatted.markdown
    
    # Vérifications contenu
    assert "- Comprendre le processus" in formatted.markdown
    assert "- Identifier les étapes" in formatted.markdown
    assert "1. Introduction" in formatted.markdown  # Numérotation du plan
    assert "2. Le processus" in formatted.markdown
    assert "3. Importance écologique" in formatted.markdown
    assert "La photosynthèse est un processus vital..." in formatted.markdown
    
    # Vérifications modèle
    assert formatted.title == "La photosynthèse expliquée"
    
    # SUPPRIMÉ: Vérifications quiz


def test_format_lesson_handles_minimal_content():
    """
    Test avec contenu minimal (edge case).
    """
    content = LessonContent(
        title="Test minimal",
        objectives=["Un seul objectif"],
        plan=["Section A", "Section B"],
        content="Contenu court.",
    )

    formatted = format_lesson(content)
    
    # Structure présente même avec contenu minimal
    assert "# Test minimal" in formatted.markdown
    assert "## Objectifs d'apprentissage" in formatted.markdown
    assert "- Un seul objectif" in formatted.markdown
    assert "1. Section A" in formatted.markdown
    assert "2. Section B" in formatted.markdown
    assert "Contenu court." in formatted.markdown