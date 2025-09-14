"""
Tests unitaires lesson_generator CORRIGÉS (sans quiz) - v0.1.2.

NETTOYAGE:
- Suppression du champ include_quiz des tests
- Focus sur la validation des enum et la qualité de génération
- Gestion d'erreurs OpenAI maintenue
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — nécessaire pour fixtures et assertions
# - unittest.mock (stdlib) : mocking des appels externes — alternative: monkeypatch mais moins expressif
# - json (stdlib) : construction réponses mock JSON
# - fastapi (tierce) : HTTPException pour vérifications erreurs
# - pydantic (tierce) : ValidationError pour vérifier les contraintes — alternative: ValueError générique
# - agents.lesson_generator (local) : module à tester
import pytest
from unittest.mock import Mock, patch
import json
from fastapi import HTTPException
from pydantic import ValidationError

from agents.lesson_generator import LessonRequest, generate_lesson, LessonContent


def test_lesson_request_validation_strict_enums():
    """Test validation stricte des enum audience/duration (SANS QUIZ)."""
    
    # Valid request (simplifié)
    valid_req = LessonRequest(
        subject="Test sujet",
        audience="lycéen", 
        duration="short"
    )
    assert valid_req.audience == "lycéen"
    assert valid_req.duration == "short"
    # SUPPRIMÉ: assert valid_req.include_quiz is True
    
    # Invalid audience
    with pytest.raises(ValueError, match="Input should be 'enfant', 'lycéen' or 'adulte'"):
        LessonRequest(subject="Test", audience="invalid", duration="short")
        
    # Invalid duration  
    with pytest.raises(ValueError, match="Input should be 'short', 'medium' or 'long'"):
        LessonRequest(subject="Test", audience="enfant", duration="invalid")


def test_lesson_request_subject_max_length():
    """Test erreur si le sujet dépasse 200 caractères."""

    long_subject = "a" * 201
    with pytest.raises(ValidationError, match="at most 200 characters"):
        LessonRequest(subject=long_subject, audience="enfant", duration="short")


@patch('agents.lesson_generator.client')
def test_generate_lesson_success_single_parsing(mock_client):
    """Test génération réussie - focus contenu de qualité."""
    
    # Mock réponse OpenAI valide
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "La physique quantique (niveau adulte)",
        "objectives": ["Comprendre les principes de base", "Découvrir les applications"],
        "plan": ["Introduction", "Principes fondamentaux", "Applications modernes"],
        "content": "# Introduction\nLa physique quantique révolutionne notre compréhension..."
    })
    mock_response.usage = Mock(total_tokens=123)
    mock_client.chat.completions.create.return_value = mock_response

    # Appel
    request = LessonRequest(subject="La physique quantique", audience="adulte", duration="medium")
    result, tokens = generate_lesson(request)

    # Vérifications
    assert isinstance(result, LessonContent)
    assert result.title == "La physique quantique (niveau adulte)"
    assert len(result.objectives) == 2
    assert len(result.plan) == 3
    assert "révolutionne notre compréhension" in result.content
    assert tokens == 123
    
    # Vérifier un seul appel OpenAI avec les bons paramètres
    mock_client.chat.completions.create.assert_called_once()
    call_args = mock_client.chat.completions.create.call_args
    assert call_args[1]["model"] == "gpt-3.5-turbo"
    assert call_args[1]["max_tokens"] == 200  # Limite MVP
    assert call_args[1]["temperature"] == 0.3


@patch('agents.lesson_generator.client')
def test_generate_lesson_missing_fields_error(mock_client):
    """Test erreur si OpenAI oublie des champs requis."""
    
    # Mock réponse incomplète (manque 'content')
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Test Title",
        "objectives": ["Obj1"],
        "plan": ["Section1"]
        # Pas de "content"!
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    request = LessonRequest(subject="Test", audience="enfant", duration="medium")
    
    # Doit lever HTTPException avec message spécifique
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
    
    assert exc_info.value.status_code == 500
    assert "champs requis" in exc_info.value.detail
    assert "content" in exc_info.value.detail


@patch('agents.lesson_generator.client')  
def test_generate_lesson_invalid_json_error(mock_client):
    """Test erreur si OpenAI retourne du JSON malformé."""
    
    # Mock réponse JSON cassée
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = '{"title": "Test", invalid json'
    mock_client.chat.completions.create.return_value = mock_response
    
    request = LessonRequest(subject="Test", audience="adulte", duration="long")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
    
    assert exc_info.value.status_code == 500
    assert "JSON invalide" in exc_info.value.detail


@patch('agents.lesson_generator.client')
def test_generate_lesson_empty_response_error(mock_client):
    """Test erreur si OpenAI retourne une réponse vide."""
    
    # Mock réponse vide
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = ""
    mock_client.chat.completions.create.return_value = mock_response
    
    request = LessonRequest(subject="Test", audience="lycéen", duration="short")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
        
    assert exc_info.value.status_code == 500
    assert "réponse vide" in exc_info.value.detail


@patch('agents.lesson_generator.client')
def test_generate_lesson_content_quality_validation(mock_client):
    """Test validation de la qualité minimale du contenu."""
    
    # Mock réponse avec contenu trop minimal
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Test",
        "objectives": [],  # Pas d'objectifs!
        "plan": ["Seule section"],  # Plan trop court!
        "content": "Contenu minimal"
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    request = LessonRequest(subject="Test", audience="enfant", duration="short")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
        
    assert exc_info.value.status_code == 500
    # Devrait échouer sur objectifs vides OU plan trop court
    assert ("objectif" in exc_info.value.detail.lower() or 
            "sections" in exc_info.value.detail.lower())


@patch('agents.lesson_generator.time.sleep', return_value=None)
@patch('agents.lesson_generator.client')
def test_generate_lesson_openai_timeout_error(mock_client, _mock_sleep):
    """Test gestion timeout OpenAI spécifique avec retry."""

    # Mock timeout exception sur chaque appel
    mock_client.chat.completions.create.side_effect = Exception("Request timed out")

    request = LessonRequest(subject="Test", audience="enfant", duration="short")

    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)

    assert exc_info.value.status_code == 504
    assert "Timeout OpenAI" in exc_info.value.detail
    assert "Réessayez" in exc_info.value.detail
    assert mock_client.chat.completions.create.call_count == 2


@patch('agents.lesson_generator.time.sleep', return_value=None)
@patch('agents.lesson_generator.client')
def test_generate_lesson_rate_limit_error(mock_client, _mock_sleep):
    """Test gestion rate limiting OpenAI avec retry."""

    # Mock rate limit exception sur chaque appel
    mock_client.chat.completions.create.side_effect = Exception("rate limit exceeded")

    request = LessonRequest(subject="Test", audience="adulte", duration="medium")

    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)

    assert exc_info.value.status_code == 429
    assert "Limite de taux" in exc_info.value.detail
    assert "Réessayez dans 1 minute" in exc_info.value.detail
    assert mock_client.chat.completions.create.call_count == 2


@patch('agents.lesson_generator.time.sleep', return_value=None)
@patch('agents.lesson_generator.client')
def test_generate_lesson_retry_success(mock_client, _mock_sleep):
    """Test qu'une erreur transitoire est retentée avant succès."""

    # Première tentative: rate limit, seconde: réponse valide
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Retry Title",
        "objectives": ["Obj"],
        "plan": ["Section 1", "Section 2"],
        "content": "Contenu après retry"
    })
    mock_response.usage = Mock(total_tokens=55)
    mock_client.chat.completions.create.side_effect = [
        Exception("rate limit exceeded"),
        mock_response,
    ]

    request = LessonRequest(subject="Retry", audience="enfant", duration="short")
    result, tokens = generate_lesson(request)

    assert isinstance(result, LessonContent)
    assert result.title == "Retry Title"
    assert mock_client.chat.completions.create.call_count == 2
    assert tokens == 55
