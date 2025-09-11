from fastapi import APIRouter

# APIRouter permet de regrouper plusieurs endpoints sous un "module".
router = APIRouter()

@router.get("/health")
def health_check() -> dict[str, str]:
    """
    Endpoint de vérification de santé de l'API.
    Retourne simplement {"status": "ok"} pour confirmer que le serveur fonctionne.
    """
    return {"status": "ok"}
