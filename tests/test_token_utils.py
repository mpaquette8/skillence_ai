# // file: tests/test_token_utils.py

"""
Tests unitaires pour les utilitaires de budget de tokens.

Vérifie l'estimation de tokens et la validation du budget de prompt.
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — assertions et gestion d'exceptions
# - fastapi (tierce) : HTTPException pour vérifier les erreurs levées
# - agents.token_utils (local) : fonctions à tester — estimation et validation
import pytest
from fastapi import HTTPException
from agents.token_utils import (
    estimate_tokens,
    validate_prompt_budget,
    MAX_PROMPT_TOKENS,
)


def test_estimate_tokens_empty_text() -> None:
    """Retourne 0 pour une chaîne vide ou espaces."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("   ") == 0


def test_estimate_tokens_long_text() -> None:
    """Calcule correctement le nombre estimé de tokens pour un texte long."""
    text = "a" * 400  # 400 caractères
    expected = int((len(text) // 4) * 1.2)
    assert estimate_tokens(text) == expected


def test_validate_prompt_budget_accepts_short_prompt() -> None:
    """Un prompt court respecte la limite et ne lève pas d'exception."""
    validate_prompt_budget("Bonjour", context={"subject": "test"})  # Ne doit pas lever


def test_validate_prompt_budget_raises_on_overflow() -> None:
    """Dépassement du budget doit lever HTTPException 413."""
    long_prompt = "a" * ((MAX_PROMPT_TOKENS + 1) * 4)
    with pytest.raises(HTTPException) as exc:
        validate_prompt_budget(long_prompt, context={"subject": "test"})
    assert exc.value.status_code == 413
