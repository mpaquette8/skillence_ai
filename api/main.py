from fastapi import FastAPI
from api.routes import health

# Création de l'application FastAPI.
# C'est l'objet central qui va gérer toutes les routes de l'API.
app = FastAPI(title="Skillence AI")

# On ajoute ici les routes définies dans api/routes/health.py.
# Elles seront accessibles sous le préfixe /v1 (ex: /v1/health).
app.include_router(health.router, prefix="/v1")
