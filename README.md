# 🎓 Skillence AI - Générateur de leçons pédagogiques

> **MVP v0.1** - Backend Python qui génère des leçons vulgarisées via l'API OpenAI

## 🚀 Démarrage rapide (5 minutes)

### 1. Installation

```bash
# Cloner le projet
git clone <repo-url>
cd skillence_ai

# Créer l'environnement Python
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou .venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copier le template de configuration
cp .env.example .env

# Éditer .env et ajouter votre clé OpenAI
nano .env  # ou votre éditeur préféré
```

Dans `.env`, remplacez :
```bash
OPENAI_API_KEY=sk-your-openai-key-here
```

> 🔑 **Récupérez votre clé OpenAI** sur https://platform.openai.com/api-keys

### 3. Démarrer le serveur

```bash
`uvicorn api.main:app --reload`
```

✅ **Succès si vous voyez :**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     skillence_ai.config - ✅ Configuration OpenAI validée
INFO:     skillence_ai.main - Database initialized - ready to serve requests
```

---

## 🧪 Tester l'API

### Health check
```bash
curl http://localhost:8000/v1/health
# Réponse: {"status":"ok"}
```

### Générer une leçon
```bash
curl -X POST http://localhost:8000/v1/lessons \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "La photosynthèse", 
    "audience": "lycéen", 
    "duration": "short"
  }'
```

**Réponse attendue :**
```json
{
  "lesson_id": "abc12345-...",
  "title": "La photosynthèse (niveau lycéen)",
  "message": "Leçon pédagogique générée avec succès",
  "from_cache": false,
  "quality": {
    "readability": {
      "flesch_kincaid_score": 72.5,
      "readability_level": "Facile",
      "word_count": 845,
      "is_appropriate_for_audience": true,
      "audience_target": "lycéen",
      "quality_message": "✅ Lisibilité adaptée au niveau lycéen (score: 72.5)"
    }
  },
  "tokens_used": 123
}
```

### Récupérer la leçon générée
```bash
curl http://localhost:8000/v1/lessons/abc12345-...
```

**Réponse :** JSON avec le contenu complet (Markdown + objectifs + plan) et les métriques `quality` (lisibilité détaillée + audience visée)

### Métriques & Logs
- `tokens_used` : total de tokens consommés lors de l'appel OpenAI (0 si retour cache)
- `quality.readability` : score Flesch-Kincaid, niveau de lisibilité, volume de mots et validation audience
- Logs middleware (`skillence_ai.requests`) : chaque requête HTTP est tracée avec un `request_id`
- Logs génération (`skillence_ai.readability`) : avertissement si la lisibilité sort de la plage recommandée
- Timeout OpenAI : 15 s maximum par génération (`OPENAI_TIMEOUT` configurable)

---

## 📡 Endpoints disponibles

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/v1/health` | GET | Vérification de santé |
| `/v1/lessons` | POST | Génère une nouvelle leçon |
| `/v1/lessons/{id}` | GET | Récupère une leçon (inclut `quality`, sans quiz) |

### Format des requêtes

**POST /v1/lessons** :
```json
{
  "subject": "string (2-200 chars)",
  "audience": "enfant|lycéen|adulte", 
  "duration": "short|medium|long"
}
```

---

## 🧪 Tests

```bash
# Lancer tous les tests
pytest -v

# Tests spécifiques
pytest tests/test_health.py -v           # Health check
pytest tests/test_api_lessons.py -v      # API endpoints
pytest tests/test_storage.py -v          # Base de données
```

**Tous les tests utilisent des mocks OpenAI** → pas besoin de clé pour les tests.

---

## 🗄️ Base de données

- **Développement** : SQLite (`skillence_ai.db`)
- **Tables** : `requests` (demandes) + `lessons` (leçons générées)
- **Migrations** : Automatiques via SQLAlchemy (MVP v0.1)

### Vérifier le contenu de la DB
```bash
# Via Python
python -c "
from storage.base import get_db_stats
print(get_db_stats())
"

# Via sqlite3 (optionnel)
sqlite3 skillence_ai.db ".tables"
```

---

## 🔧 Configuration avancée

### Variables d'environnement (.env)

```bash
# === Obligatoire ===
OPENAI_API_KEY=sk-...                    # Clé API OpenAI

# === Optionnel ===
DATABASE_URL=sqlite:///./skillence_ai.db # Chemin base de données
LOG_LEVEL=INFO                           # DEBUG|INFO|WARNING|ERROR
OPENAI_TIMEOUT=15                        # Timeout en secondes
DEBUG_MODE=false                         # Logs SQL détaillés
```

### Personnalisation du serveur
```bash
# Port personnalisé
uvicorn api.main:app --port 8080

# Accès depuis l'extérieur
uvicorn api.main:app --host 0.0.0.0

# Mode production
uvicorn api.main:app --workers 4 --no-reload
```

---

## 🐛 Troubleshooting

### ❌ Erreur : "OPENAI_API_KEY manquante"
```bash
# Solution 1: Vérifier .env existe
ls -la .env

# Solution 2: Vérifier le contenu
cat .env | grep OPENAI

# Solution 3: Recharger les variables
source .env  # puis relancer uvicorn
```

### ❌ Erreur : "Invalid OpenAI response" 
- **Cause** : Clé API invalide ou quota dépassé
- **Solution** : Vérifiez sur https://platform.openai.com/usage

### ❌ Erreur : "Database locked"
```bash
# Arrêter tous les processus uvicorn
pkill -f uvicorn

# Supprimer le fichier DB (perte de données !)
rm skillence_ai.db

# Relancer
`uvicorn api.main:app --reload`
```

### ❌ Tests qui échouent
```bash
# Nettoyer et réinstaller
pip uninstall -r requirements.txt -y
pip install -r requirements.txt

# Vérifier Python 3.11+
python --version
```

---

## 🏗️ Architecture (MVP v0.1)

```
skillence_ai/
├── api/
│   ├── main.py              # Application FastAPI
│   ├── services/lessons.py  # Orchestration métier
│   └── middleware/logging.py # Logs + correlation ID
├── agents/
│   ├── lesson_generator.py  # Appel OpenAI + validation
│   └── formatter.py         # Format Markdown
├── storage/
│   ├── base.py             # Config DB + sessions
│   └── models.py           # ORM Request/Lesson
└── tests/                  # Tests pytest
```

**Principes** :
- ✅ **KISS** : Architecture simple, 2 agents seulement
- ✅ **SQLite** : Pas de complexité DB prématurée  
- ✅ **Synchrone** : Pas de parallélisme pour v0.1
- ✅ **Testé** : Coverage complète des endpoints

---

## 📊 Limitations MVP v0.1

- **2000 tokens max** par leçon (limite OpenAI)
- **15 secondes timeout** par génération
- **Pas de parallélisme** (1 leçon = 1 requête séquentielle)
- **SQLite uniquement** (pas de scalabilité multi-utilisateur)
- **Pas de vérification** des sources (génération "best effort")

---

## 🚀 Prochaines versions (roadmap)

- **v0.2** : Agent `verifier` + sources obligatoires
- **v0.3** : PostgreSQL + Redis + métriques avancées  
- **v0.4** : RAG vectoriel (OpenAlex/ArXiv)

---

## 🤝 Contribution

Le projet suit une approche **MVP strict** :
1. Lisez `MVP.md` pour les contraintes
2. Respectez `agent.md` pour le style de code
3. Tests obligatoires pour tout nouveau endpoint
4. Imports commentés + docstrings pédagogiques

---

## 📄 Licence

À définir - Propriété Maxime (owner)

## Interface web (auth lien magique)

1. Lancer `uvicorn api.main:app --reload`.
2. Ouvrir http://localhost:8000/web/login et soumettre un e-mail.
3. Consulter les logs (logger 'skillence_ai.web') pour r�cup�rer l'URL /web/login/callback?token=....
4. Recharger /web/dashboard pour v�rifier la session.

> ??  Pour le MVP, l'envoi d'e-mail est simul� via les logs (aucun SMTP).
## Procedure de migration (auth lien magique)

1. **Sauvegarder la base actuelle**
   ```bash
   cp skillence_ai.db skillence_ai.db.backup
   ```
2. **Executer le script d'initialisation** (cree `users`, `login_tokens`, `sessions` si absentes)
   ```bash
   python scripts/init_users_tables.py
   ```
3. **Verifier**
   ```bash
   sqlite3 skillence_ai.db ".tables"
   # ou
   python -c "from storage.base import get_db_stats; print(get_db_stats())"
   ```
4. **Rollback rapide**
   ```bash
   mv skillence_ai.db.backup skillence_ai.db
   ```
