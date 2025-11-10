# // file: scripts/init_users_tables.py
"""
Initialise les tables d’authentification (users/login_tokens/sessions) dans la
base SQLite existante.

Usage:
    python scripts/init_users_tables.py

Le script est idempotent : il crée les tables si elles n’existent pas encore.
"""

# Inventaire des dépendances
# - sqlalchemy.schema (tierce) : MetaData pour cibler des tables spécifiques
# - storage.base (local) : engine + Base pour accéder à la configuration DB
# - storage.models (local) : garantit que les modèles sont enregistrés sur Base.metadata
from sqlalchemy.schema import MetaData

from storage.base import Base, engine
import storage.models  # noqa: F401 - enregistre les modèles sur Base.metadata


def main() -> None:
    """Crée les tables users/login_tokens/sessions si absentes."""
    metadata: MetaData = Base.metadata

    target_tables = [
        metadata.tables.get("users"),
        metadata.tables.get("login_tokens"),
        metadata.tables.get("sessions"),
    ]
    tables_to_create = [t for t in target_tables if t is not None]

    if not tables_to_create:
        print("Aucune table ciblée trouvée sur le metadata, arrêt.")
        return

    metadata.create_all(bind=engine, tables=tables_to_create)
    print("Tables d'authentification initialisées (users/login_tokens/sessions).")


if __name__ == "__main__":
    main()
