# // file: api/middleware/logging.py

"""
Middleware de logging avec correlation ID.
Génère un ID unique par requête et l'injecte dans tous les logs.
"""

# Inventaire des dépendances
# - fastapi (tierce) : Request, Response pour middleware — nécessaire pour intercepter requêtes
# - starlette.middleware.base (tierce) : BaseHTTPMiddleware — classe de base pour middleware
# - uuid (stdlib) : génération d'ID unique — alternative: time.time() mais moins lisible
# - time (stdlib) : mesure de durée — alternative: datetime mais plus lourd
# - logging (stdlib) : système de logs — alternative: print() mais pas configurable
# - contextvars (stdlib) : variables contextuelles async-safe — alternative: threading.local mais pas async
from fastapi import Request, Response  # tierce — types FastAPI
from starlette.middleware.base import BaseHTTPMiddleware  # tierce — base middleware
import uuid  # stdlib — ID unique
import time  # stdlib — timing
import logging  # stdlib — logs
from contextvars import ContextVar  # stdlib — contexte async

# Variable contextuelle pour stocker le request_id dans le contexte async
request_id_var: ContextVar[str] = ContextVar("request_id", default="")

# Logger configuré pour ce module
logger = logging.getLogger("skillence_ai.requests")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui ajoute un request_id à chaque requête et log les opérations.
    
    Fonctionnalités :
    - Génère un UUID court par requête
    - Stocke l'ID dans le contexte async (accessible partout)
    - Log début/fin de requête avec timing
    - Format simple : [REQUEST abc123] message
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Générer un ID unique court (8 premiers caractères de l'UUID)
        request_id = str(uuid.uuid4())[:8]
        
        # Stocker dans le contexte async
        request_id_var.set(request_id)
        
        # Log début de requête
        start_time = time.time()
        logger.info(f"[REQUEST {request_id}] {request.method} {request.url.path} started")
        
        try:
            # Traiter la requête
            response = await call_next(request)
            
            # Log fin de requête avec durée
            duration_ms = int((time.time() - start_time) * 1000)
            logger.info(
                f"[REQUEST {request_id}] {request.method} {request.url.path} "
                f"completed ({response.status_code}) - {duration_ms}ms"
            )
            
            return response
            
        except Exception as exc:
            # Log en cas d'erreur
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[REQUEST {request_id}] {request.method} {request.url.path} "
                f"failed: {str(exc)} - {duration_ms}ms"
            )
            raise


def get_request_id() -> str:
    """
    Récupère le request_id du contexte actuel.
    Utilisable dans n'importe quel service/agent.
    
    Returns:
        ID de la requête courante, ou chaîne vide si pas de contexte
    """
    return request_id_var.get()


def log_operation(operation: str, duration_ms: int = None, **kwargs) -> None:
    """
    Log une opération avec le request_id automatique.
    
    Args:
        operation: nom de l'opération (ex: "agent_generation")
        duration_ms: durée optionnelle en millisecondes
        **kwargs: données supplémentaires à logger
    """
    request_id = get_request_id()
    
    # Construire le message
    msg_parts = [f"[REQUEST {request_id}]", operation]
    
    if duration_ms is not None:
        msg_parts.append(f"({duration_ms}ms)")
    
    # Ajouter les données supplémentaires
    if kwargs:
        extras = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        msg_parts.append(f"- {extras}")
    
    message = " ".join(msg_parts)
    logger.info(message)