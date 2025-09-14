# // file: agents/quality_utils.py

"""
Utilitaires de qualité pédagogique — Score Flesch-Kincaid MVP v0.1.

RÔLE: Valider la lisibilité du contenu selon l'audience cible.
FOCUS v0.1: Implémentation simple et fiable, seuils adaptés au français.

TRADE-OFFS: 
- Formule FK adaptée français vs anglais original (coefficients ajustés)
- Validation stricte vs souple (MVP = warnings, pas blocage)
- Regex simple vs parser syntaxique complexe (suffisant pour MVP)
"""

# Inventaire des dépendances
# - re (stdlib) : expressions régulières pour parsing texte — alternative: spacy mais trop lourd
# - typing (stdlib) : annotations de types — améliore lisibilité
# - dataclasses (stdlib) : structure de données simple — alternative: Pydantic mais redondant ici
# - math (stdlib) : opérations mathématiques (moyenne) — nécessaire pour formule FK
import re
from typing import Tuple, Dict, List
from dataclasses import dataclass
import math


# Seuils Flesch-Kincaid adaptés au français (selon recherches pédagogiques)
FK_THRESHOLDS = {
    "enfant": {
        "min": 80,      # Très facile à lire
        "max": 100,     # Extrêmement facile
        "description": "Phrases courtes, mots simples, analogies concrètes"
    },
    "lycéen": {
        "min": 60,      # Assez facile à lire
        "max": 80,      # Facile à lire
        "description": "Vocabulaire étendu, concepts abstraits accessibles"
    },
    "adulte": {
        "min": 40,      # Difficile à lire
        "max": 70,      # Assez facile à lire
        "description": "Terminologie technique, raisonnements complexes acceptés"
    }
}


@dataclass
class ReadabilityScore:
    """Résultat d'analyse de lisibilité."""
    flesch_kincaid: float
    word_count: int
    sentence_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    is_valid_for_audience: bool
    validation_message: str
    audience_target: str


def count_syllables(word: str) -> int:
    """
    Compte les syllabes dans un mot français (approximation simple).
    
    MÉTHODE: Compte les voyelles consécutives comme une syllabe.
    Plus précis que "1 voyelle = 1 syllabe" mais moins lourd qu'un dictionnaire.
    
    Args:
        word: Mot à analyser (nettoyé, sans ponctuation)
        
    Returns:
        Nombre de syllabes estimé (minimum 1)
    """
    if not word or len(word) < 2:
        return 1
    
    word = word.lower()
    vowels = "aeiouàáâäèéêëìíîïòóôöùúûü"
    
    syllable_count = 0
    prev_was_vowel = False
    
    for char in word:
        is_vowel = char in vowels
        if is_vowel and not prev_was_vowel:
            syllable_count += 1
        prev_was_vowel = is_vowel
    
    # Au moins 1 syllabe par mot
    return max(1, syllable_count)


def parse_text_stats(text: str) -> Tuple[int, int, float, float]:
    """
    Extrait les statistiques de base d'un texte pour calcul FK (VERSION MVP ROBUSTE).
    
    Args:
        text: Contenu markdown à analyser
        
    Returns:
        (nb_mots, nb_phrases, moy_mots_par_phrase, moy_syllabes_par_mot)
    """
    if not text or not text.strip():
        return 0, 0, 0.0, 0.0
    
    # Nettoyage markdown plus strict
    cleaned = re.sub(r'#{1,6}\s*', '', text)  # Headers
    cleaned = re.sub(r'[*_`\[\]]+', '', cleaned)  # Formatage
    cleaned = re.sub(r'\n+', ' ', cleaned)  # Retours ligne -> espaces
    cleaned = re.sub(r'\s+', ' ', cleaned.strip())  # Espaces multiples
    
    if not cleaned or len(cleaned.strip()) < 2:
        return 0, 0, 0.0, 0.0
    
    # Compter phrases (plus strict)
    sentences = re.split(r'[.!?]+', cleaned)
    sentences = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 2]
    sentence_count = len(sentences)
    
    if sentence_count == 0:
        return 0, 0, 0.0, 0.0
    
    # Compter mots (lettres françaises + minimum 2 caractères)
    words = re.findall(r"[a-zA-ZàâäéèêëïîôöùûüçÀÂÄÉÈÊËÏÎÔÖÙÛÜÇ]{2,}", cleaned)
    word_count = len(words)
    
    if word_count == 0:
        return word_count, sentence_count, 0.0, 0.0
    
    # Statistiques moyennes
    avg_words_per_sentence = word_count / sentence_count
    
    # Compter syllabes totales
    total_syllables = sum(count_syllables(word) for word in words)
    avg_syllables_per_word = total_syllables / word_count if word_count > 0 else 0.0
    
    return word_count, sentence_count, avg_words_per_sentence, avg_syllables_per_word


def calculate_flesch_kincaid_french(text: str) -> float:
    """
    Calcule le score Flesch-Kincaid adapté au français.
    
    FORMULE adaptée: 207 - (1.015 × mots/phrase) - (84.6 × syllabes/mot)
    (Coefficients ajustés pour les spécificités du français vs anglais original)
    
    Args:
        text: Contenu à analyser
        
    Returns:
        Score FK (0-100, plus élevé = plus facile à lire)
    """
    word_count, sentence_count, avg_words_per_sentence, avg_syllables_per_word = parse_text_stats(text)
    
    if word_count == 0 or sentence_count == 0:
        return 0.0
    
    # Formule FK adaptée français
    fk_score = 207 - (1.015 * avg_words_per_sentence) - (84.6 * avg_syllables_per_word)
    
    # Borner entre 0 et 100
    return max(0.0, min(100.0, fk_score))


def validate_readability_for_audience(text: str, audience: str) -> ReadabilityScore:
    """
    Valide la lisibilité d'un texte pour une audience donnée.
    
    FOCUS MVP: Warnings informatifs, pas de blocage strict.
    
    Args:
        text: Contenu à analyser (markdown accepté)
        audience: "enfant", "lycéen", ou "adulte"
        
    Returns:
        Analyse complète avec validation et recommandations
    """
    if audience not in FK_THRESHOLDS:
        raise ValueError(f"Audience '{audience}' non supportée. Choix: {list(FK_THRESHOLDS.keys())}")
    
    # Calcul des métriques
    word_count, sentence_count, avg_words_per_sentence, avg_syllables_per_word = parse_text_stats(text)
    fk_score = calculate_flesch_kincaid_french(text)
    
    # Validation selon audience
    thresholds = FK_THRESHOLDS[audience]
    is_valid = thresholds["min"] <= fk_score <= thresholds["max"]
    
    # Message de validation pédagogique
    if is_valid:
        validation_message = f"✅ Lisibilité adaptée au niveau {audience} (score: {fk_score:.1f})"
    elif fk_score < thresholds["min"]:
        validation_message = (
            f"⚠️ Texte trop difficile pour {audience} (score: {fk_score:.1f}, attendu: ≥{thresholds['min']})\n"
            f"💡 Suggestions: raccourcir les phrases ({avg_words_per_sentence:.1f} mots/phrase), "
            f"utiliser des mots plus simples"
        )
    else:  # fk_score > max
        validation_message = (
            f"ℹ️ Texte très facile pour {audience} (score: {fk_score:.1f}, max recommandé: {thresholds['max']})\n"
            f"💡 Peut être enrichi avec du vocabulaire plus spécialisé"
        )
    
    return ReadabilityScore(
        flesch_kincaid=fk_score,
        word_count=word_count,
        sentence_count=sentence_count,
        avg_words_per_sentence=avg_words_per_sentence,
        avg_syllables_per_word=avg_syllables_per_word,
        is_valid_for_audience=is_valid,
        validation_message=validation_message,
        audience_target=audience
    )


def get_readability_summary(score: ReadabilityScore) -> Dict[str, any]:
    """
    Résumé des métriques de lisibilité pour l'API (format simple).
    
    Args:
        score: Résultat d'analyse de lisibilité
        
    Returns:
        Dictionnaire avec métriques essentielles pour réponse API
    """
    return {
        "flesch_kincaid_score": round(score.flesch_kincaid, 1),
        "readability_level": _get_readability_level(score.flesch_kincaid),
        "word_count": score.word_count,
        "is_appropriate_for_audience": score.is_valid_for_audience,
        "audience_target": score.audience_target,
        "quality_message": score.validation_message.split('\n')[0]  # Première ligne seulement
    }


def _get_readability_level(fk_score: float) -> str:
    """Convertit un score FK en niveau de lisibilité textuel."""
    if fk_score >= 80:
        return "Très facile"
    elif fk_score >= 60:
        return "Facile"
    elif fk_score >= 40:
        return "Assez difficile"
    elif fk_score >= 20:
        return "Difficile"
    else:
        return "Très difficile"