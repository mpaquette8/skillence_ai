# // file: tests/test_lesson_generator.py

"""
Tests unitaires pour l'agent lesson_generator (post-fix).
Valide la correction du double parsing et la gestion d'erreurs améliorée.
"""

# Inventaire des dépendances
# - pytest (tierce) : framework de tests — nécessaire pour fixtures et assertions
# - unittest.mock (stdlib) : mocking des appels externes — alternative: monkeypatch mais moins expressif
# - json (stdlib) : construction réponses mock JSON
# - fastapi (tierce) : HTTPException pour vérifications erreurs
# - agents.lesson_generator (local) : module à tester
import pytest
from unittest.mock import Mock, patch
import json
from fastapi import HTTPException

from agents.lesson_generator import LessonRequest, generate_lesson, LessonContent


def test_lesson_request_validation_strict_enums():
    """Test validation stricte des enum audience/duration."""
    
    # Valid request
    valid_req = LessonRequest(
        subject="Test sujet",
        audience="lycéen", 
        duration="short"
    )
    assert valid_req.audience == "lycéen"
    assert valid_req.duration == "short"
    
    # Invalid audience
    with pytest.raises(ValueError, match="Input should be 'enfant', 'lycéen' or 'adulte'"):
        LessonRequest(subject="Test", audience="invalid", duration="short")
        
    # Invalid duration  
    with pytest.raises(ValueError, match="Input should be 'short', 'medium' or 'long'"):
        LessonRequest(subject="Test", audience="enfant", duration="invalid")


@patch('agents.lesson_generator.client')
def test_generate_lesson_success_single_parsing(mock_client):
    """Test génération réussie - vérifie qu'on ne parse JSON qu'une fois."""
    
    # Mock réponse OpenAI valide
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Test Title",
        "objectives": ["Obj1", "Obj2"], 
        "plan": ["Section1", "Section2", "Section3"],
        "content": "Test content"
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    # Appel
    request = LessonRequest(subject="Test", audience="lycéen", duration="short")
    result = generate_lesson(request)
    
    # Vérifications
    assert isinstance(result, LessonContent)
    assert result.title == "Test Title"
    assert result.objectives == ["Obj1", "Obj2"]
    assert len(result.plan) == 3
    assert result.content == "Test content"
    
    # Vérifier un seul appel OpenAI
    mock_client.chat.completions.create.assert_called_once()


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
def test_generate_lesson_openai_timeout_error(mock_client):
    """Test gestion timeout OpenAI spécifique."""
    
    # Mock timeout exception (OpenAI client peut lever différents types)
    mock_client.chat.completions.create.side_effect = Exception("Request timed out")
    
    request = LessonRequest(subject="Test", audience="enfant", duration="short")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
        
    assert exc_info.value.status_code == 504
    assert "Timeout OpenAI" in exc_info.value.detail
    assert "Réessayez" in exc_info.value.detail


@patch('agents.lesson_generator.client')
def test_generate_lesson_rate_limit_error(mock_client):
    """Test gestion rate limiting OpenAI."""
    
    # Mock rate limit exception
    mock_client.chat.completions.create.side_effect = Exception("rate limit exceeded")
    
    request = LessonRequest(subject="Test", audience="adulte", duration="medium")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
        
    assert exc_info.value.status_code == 429
    assert "Limite de taux" in exc_info.value.detail
    assert "Réessayez dans 1 minute" in exc_info.value.detail


@patch('agents.lesson_generator.client')
def test_generate_lesson_wrong_types_validation(mock_client):
    """Test validation des types de champs (objectives/plan doivent être des listes)."""
    
    # Mock réponse avec mauvais types
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = json.dumps({
        "title": "Test Title",
        "objectives": "Not a list!",  # String au lieu de List[str]
        "plan": ["Section1", "Section2"],
        "content": "Test content"
    })
    mock_client.chat.completions.create.return_value = mock_response
    
    request = LessonRequest(subject="Test", audience="lycéen", duration="long")
    
    with pytest.raises(HTTPException) as exc_info:
        generate_lesson(request)
        
    assert exc_info.value.status_code == 500
    assert "objectives" in exc_info.value.detail
    assert "liste" in exc_info.value.detail