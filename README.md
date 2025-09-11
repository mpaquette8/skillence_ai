# Skillence_AI

## 🚀 Quick Start

### Installation
```bash
git clone <repo-url>
cd skillence_ai
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Ajoutez votre clé OpenAI
OPENAI_API_KEY=sk-...
```

### Lancer le serveur
```bash
uvicorn api.main:app --reload
```

### Tester l'API
```bash
curl -X POST http://localhost:8000/v1/lessons \
  -H "Content-Type: application/json" \
  -d '{"subject":"La photosynthèse","audience":"lycéen","duration":"short"}'
```

### Endpoints disponibles
- `GET /v1/health` : vérification simple
- `POST /v1/lessons` : génère une nouvelle leçon
- `GET /v1/lessons/{id}` : récupère la leçon générée
