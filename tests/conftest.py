"""
Configuration pytest GLOBALE (mise à jour).
Ajoute les fixtures de config de test + mock OpenAI automatique.
"""

import json
from types import SimpleNamespace
import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True, scope="session")  # Appliqué automatiquement à TOUS les tests
def mock_openai_config_validation():
    """
    Mock global de la validation OpenAI pour TOUS les tests.
    Évite les erreurs de clé manquante en environnement CI/CD.
    """
    with patch('storage.base.Settings.validate_openai_config', return_value=None):
        yield


@pytest.fixture(autouse=True)
def mock_openai_client():
    """Mock automatique du client OpenAI pour tous les tests."""
    def fake_create(*args, **kwargs):
        messages = kwargs.get("messages", [])
        content = messages[0]["content"] if messages else ""
        subject = audience = ""
        
        for line in content.splitlines():
            if line.startswith("Sujet:"):
                subject = line.split(":", 1)[1].strip()
            elif line.startswith("Audience:"):
                audience = line.split(":", 1)[1].strip()
        
        # Réponse factice mais réaliste
        payload = {
            "title": f"{subject} (niveau {audience})" if subject and audience else "Leçon de test",
            "objectives": ["Objectif pédagogique 1", "Objectif 2"],
            "plan": ["Introduction", "Développement", "Conclusion"],
            "content": f"# {subject}\n\nContenu pédagogique détaillé sur {subject} adapté au niveau {audience}."
        }
        
        response = SimpleNamespace()
        response.choices = [SimpleNamespace()]
        response.choices[0].message = SimpleNamespace()
        response.choices[0].message.content = json.dumps(payload)
        
        return response

    with patch('agents.lesson_generator.client.chat.completions.create', side_effect=fake_create):
        yield