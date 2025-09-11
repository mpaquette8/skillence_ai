skillence_ai/
  api/                # Application FastAPI (endpoints, routes)
    main.py           # Point d’entrée de l’API (création de l'app)
    routes/
      health.py       # Endpoint GET /v1/health
  storage/            # Gestion de la base SQLite (à venir)
    base.py           # Config SQLAlchemy (connexion DB)
    models.py         # Définition des tables ORM (Lesson, Request)
  tests/              # Tests avec pytest
    test_health.py    # Test du health check
  requirements.txt    # Dépendances Python
  .gitignore          # Fichiers/dossiers ignorés par Git
  README.md           # Documentation du projet
  .venv/              # Environnement virtuel local (non versionné)