# SKILLENCE_AI — MVP.md (version simplifiée)

**But** : Avoir une première version fonctionnelle en 2–3 semaines pour valider le concept de vulgarisation multi‑agents.

---

## 🎯 Objectif MVP
- Générer une leçon simple (plan + contenu + quiz basique) à partir d’un sujet.
- Produire un Markdown structuré exportable.

---

## ⚙️ Stack minimale
- Python 3.11+, FastAPI, Pydantic v2
- SQLite (2 tables : lessons, requests)
- API GPT (tool calling basique)
- Logs simples (logging INFO)
- Tests basiques avec pytest + httpx


---

## 📝 Exemple concret

**POST /v1/lessons**

```json
{
  "subject": "La photosynthèse",
  "audience": "lycéen",
  "duration": "short"
}
```

**Réponse attendue (Markdown simplifié)**

```
# La photosynthèse (niveau lycéen)

## Objectifs
- Comprendre le rôle du soleil
- Identifier les étapes principales

## Plan
1. Introduction
2. Les étapes de la photosynthèse
3. Son importance écologique

## Contenu (~500 mots)
Texte vulgarisé ici…

## Quiz (5 QCM)
1. Quelle molécule est produite ?
...
```

---

## 💰 Budget & limites

- Max **2000 tokens** par leçon (hard stop)
- Timeout **15s** par appel LLM
- Latence totale cible < 30s
---

## 🧩 Agents (ultra-simplifiés)
- `lesson_generator` : fait le plan + écrit les sections
- `formatter` : assemble en Markdown + génère un quiz simple (5 QCM)

*(Les autres agents — verifier, parallélisme, cache Redis — viendront plus tard.)*

---

## 📡 Endpoints API
- `GET /v1/health` : ping
- `POST /v1/lessons` : crée une leçon, renvoie `lesson_id`
- `GET /v1/lessons/{id}` : récupère la leçon (markdown + meta)

---

## ✅ Must / Should / Could / Won’t (MoSCoW)

### Must (absolus)
- FastAPI en place avec health check
- POST /v1/lessons qui génère une leçon complète (plan + texte)
- SQLite pour stocker les leçons
- Logs simples (INFO)
- Tests : health + happy path

### Should (souhaitables)
- Quiz basique intégré dans le markdown

### Could (optionnels)
- Idempotence simple (hash d’entrée)
- Score de lisibilité FK
- Rubrics qualité
- Export PDF

### Won’t (pour plus tard)
- Redis, Postgres, parallélisme, observabilité avancée
- Vérification stricte des sources
- RAG vectoriel

---

## 🚀 Plan d’action (3 semaines)

**Semaine 1**
- Setup FastAPI minimal + health check
- Table `lessons` + `requests` dans SQLite
- Test e2e avec leçon hardcodée

**Semaine 2**
- Intégration GPT avec tool calling
- Génération dynamique de leçon (sans sources)
- Endpoint POST /v1/lessons opérationnel

**Semaine 3**
- Formatter Markdown + quiz QCM simple
- Tests supplémentaires + documentation

---

## 📊 Métriques simples
- Temps de génération par leçon
- Nombre de tokens utilisés
- Taille (nb de mots) du contenu produit

---

## 🔒 Garde-fous
- Pas de secrets en dur (API key via .env)
- Timeout court par appel LLM
- Message d’erreur clair si génération échoue

---
