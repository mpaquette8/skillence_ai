# // file: api/services/__init__.py

"""
Services d'orchestration (logique métier).

Ce package contient les services qui coordonnent :
- Les agents (génération de contenu)  
- La persistance (base de données)
- Les transformations (DTOs, formatage)

Évite de mettre la logique métier directement dans les routes FastAPI.
"""