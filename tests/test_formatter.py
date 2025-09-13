# // file: tests/test_formatter.py
import re
from agents.lesson_generator import LessonContent
from agents.formatter import format_lesson

def test_format_lesson_creates_markdown_and_quiz():
    content = LessonContent(
        title="Test",
        objectives=["A", "B"],
        plan=["Intro", "Fin"],
        content="Corps de texte",
    )

    formatted = format_lesson(content)

    # Markdown
    assert formatted.markdown.startswith("# Test")
    assert "## Objectifs" in formatted.markdown
    assert "Corps de texte" in formatted.markdown

    # Quiz
    assert len(formatted.quiz) == 5
    for item in formatted.quiz:
        assert len(item.options) == 4
        assert 0 <= item.answer_index < 4
        # question reprenant le titre
        assert re.search(r"Test", item.question)
