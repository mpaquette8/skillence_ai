# // file: agents/token_utils.py

"""
Utilitaires de gestion du budget de tokens (limite MVP 2000).

RÔLE: Éviter les coûts incontrôlés et timeouts OpenAI en validant 
la taille du prompt AVANT l'appel API.

TRADE-OFFS: Approximation simple vs tokenizer exact (tiktoken), 
mais suffisant pour la limite MVP et compatible avec toutes les versions OpenAI.
"""

# Inventaire des dépendances
# - re (stdlib) : expressions régulières pour nettoyage texte — alternative: str.replace() mais moins flexible
# - typing (stdlib) : annotations de types — améliore lisibilité du code
# - fastapi (tierce) : HTTPException pour erreurs API — standard FastAPI pour retour utilisateur
import re
from typing import Dict, Any
from fastapi import HTTPException


# Constantes MVP (selon MVP.md)
MAX_TOKENS_PER_REQUEST = 2000  # Budget strict par requête
TOKEN_SAFETY_MARGIN = 200      # Marge pour la réponse OpenAI
MAX_PROMPT_TOKENS = MAX_TOKENS_PER_REQUEST - TOKEN_SAFETY_MARGIN  # 1800 tokens max pour prompt


def estimate_tokens(text: str) -> int:
    """
    Estimation rapide du nombre de tokens (approximation 1 token ≈ 4 caractères).
    
    Alternative plus précise: tiktoken d'OpenAI, mais ajoute une dépendance lourde.
    L'approximation 4 chars/token est suffisante pour la validation MVP.
    
    Args:
        text: Texte à analyser
        
    Returns:
        Nombre estimé de tokens
    """
    if not text or not text.strip():
        return 0
    
    # Nettoyage basique (espaces multiples, retours à la ligne)
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Estimation conservative: 4 caractères ≈ 1 token
    # Plus précis que "1 mot = 1 token" car tient compte de la ponctuation
    estimated_tokens = len(cleaned) // 4
    
    # Marge d'erreur +20% pour être conservateur
    return int(estimated_tokens * 1.2)


def validate_prompt_budget(prompt: str, context: Dict[str, Any] = None) -> None:
    """
    Valide que le prompt respecte le budget de tokens MVP.
    
    Lève HTTPException si dépassement pour retourner une erreur claire à l'utilisateur.
    
    Args:
        prompt: Prompt complet à envoyer à OpenAI
        context: Contexte pour logs (subject, audience, etc.)
        
    Raises:
        HTTPException: Si prompt trop long (413 Request Entity Too Large)
    """
    if not prompt:
        return
        
    token_count = estimate_tokens(prompt)
    
    if token_count > MAX_PROMPT_TOKENS:
        # Contexte pour erreur utilisateur
        ctx_info = ""
        if context:
            subject = context.get("subject", "")[:50]
            if subject:
                ctx_info = f" pour '{subject}'"
                
        raise HTTPException(
            status_code=413,  # Request Entity Too Large
            detail=(
                f"⚠️ Prompt trop long: {token_count} tokens (limite: {MAX_PROMPT_TOKENS})\n\n"
                f"🛠️ Solutions{ctx_info}:\n"
                f"• Raccourcir le sujet (actuellement: {len(context.get('subject', ''))} caractères)\n"
                f"• Choisir une durée plus courte\n"
                f"• Reformuler avec des termes plus simples\n\n"
                f"💡 Budget MVP: {MAX_TOKENS_PER_REQUEST} tokens max par leçon"
            )
        )