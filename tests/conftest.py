import json
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def mock_openai(monkeypatch):
    """Mocke l'appel OpenAI pour des tests déterministes."""
    def fake_create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        content = messages[0]["content"] if messages else ""
        subject = audience = ""
        for line in content.splitlines():
            if line.startswith("Sujet:"):
                subject = line.split(":", 1)[1].strip()
            if line.startswith("Audience:"):
                audience = line.split(":", 1)[1].strip()
        payload = {
            "title": f"{subject} (niveau {audience})",
            "objectives": ["Obj1", "Obj2"],
            "plan": ["Introduction", "Développement", "Conclusion"],
            "content": f"Contenu sur {subject} pour {audience}"
        }
        data = json.dumps(payload)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=data))])

    monkeypatch.setattr(
        "agents.lesson_generator.client.chat.completions.create",
        fake_create,
    )
