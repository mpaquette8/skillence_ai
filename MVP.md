# SKILLENCE_AI — MVP.md

**But** : Avoir une première version fonctionnelle en 2–3 semaines pour valider le concept de **vulgarisation de qualité** multi‑agents.

---

## 🎯 Objectif MVP (révisé)
- Générer une **leçon vulgarisée de qualité** (plan + contenu structuré) à partir d'un sujet.
- Produire un **Markdown pédagogique** exportable avec score de lisibilité.
- **Focus v0.1** : Excellence du contenu explicatif plutôt que fonctionnalités annexes.

---

## ⚙️ Stack minimale
- Python 3.11+, FastAPI, Pydantic v2
- SQLite (2 tables : lessons, requests)
- API GPT (tool calling basique)
- Logs simples (logging INFO)
- Tests basiques avec pytest + httpx
- **Nouveau** : Calcul Flesch-Kincaid pour validation qualité

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

**Réponse attendue (Markdown optimisé)**

```
# La photosynthèse (niveau lycéen)

## Objectifs d'apprentissage
- Comprendre le rôle de la lumière solaire
- Identifier les étapes principales du processus
- Saisir l'importance écologique

## Plan de la leçon
1. Qu'est-ce que la photosynthèse ?
2. Les acteurs principaux (chloroplaste, chlorophylle)
3. Les deux phases : claire et sombre
4. Impact sur l'écosystème

## Contenu (~500-800 mots selon durée)
### 1. Qu'est-ce que la photosynthèse ?

La photosynthèse est comme une "cuisine" que font les plantes...
[Contenu vulgarisé avec analogies, exemples concrets]

### 2. Les acteurs principaux
[Développement structuré par section]

## Métriques qualité
- **Lisibilité** : 65/100 (Flesch-Kincaid) ✅ Adapté lycéen
- **Longueur** : 847 mots | **Tokens utilisés** : 1,200/2,000
```

---

## 💰 Budget & limites (renforcées)

- Max **2000 tokens** par leçon (**hard stop implémenté**)
- Timeout **15s** par appel LLM (**avec retry**)
- Latence totale cible < 30s
- **Nouveau** : Validation taille input (subject max 200 chars)
- **Nouveau** : Score FK minimum selon audience

---

## 🧩 Agents (recentrés qualité)
- `lesson_generator` : génère plan + sections vulgarisées **avec contrôle qualité**
- `formatter` : assemble en Markdown **structuré + calcul métriques**

*(Quiz déplacé en v0.2 — focus v0.1 sur l'excellence du contenu explicatif)*

---

## 📡 Endpoints API
- `GET /v1/health` : ping
- `POST /v1/lessons` : crée une leçon, renvoie `lesson_id` + **métriques qualité**
- `GET /v1/lessons/{id}` : récupère la leçon (markdown + méta + **score FK**)

---

## ✅ Must / Should / Could / Won't (MoSCoW révisé)

### Must (absolus — v0.1)
- FastAPI en place avec health check ✅
- POST /v1/lessons qui génère une **leçon structurée de qualité** ✅
- **Limite 2000 tokens implémentée** (hard stop)
- **Score Flesch-Kincaid** calculé et validé
- **Validation stricte inputs** (subject 200 chars max)
- SQLite pour stocker les leçons ✅
- Logs simples (INFO) ✅
- Tests : health + happy path ✅

### Should (souhaitables — v0.1)
- Idempotence simple (hash d'entrée) ✅
- Métriques de performance dans les logs ✅
- **Analogies et exemples** adaptés à l'audience

### Could (optionnels — reportés v0.2)
- ~~Quiz basique~~ → v0.2 avec agent `quizzer` dédié
- Export PDF → v0.2
- Rubrics qualité avancées → v0.2

### Won't (pour plus tard)
- Redis, Postgres, parallélisme, observabilité avancée → v0.3
- Vérification stricte des sources → v0.2 avec agent `verifier`
- RAG vectoriel → v0.3

---

## 🚀 Plan d'action ajusté (3 semaines → finition v0.1)

**Semaine 1-2** ✅ **FAIT**
- Setup FastAPI + SQLite + tests
- Agents fonctionnels + endpoints

**Semaine 3** 🔥 **EN COURS** 
- **Implémentation limite 2000 tokens** (priorité 1)
- **Score Flesch-Kincaid** + validation qualité (priorité 2)
- **Validation inputs stricte** (priorité 3)
- **Polish du formatting** Markdown (priorité 4)

---

## 📊 Métriques simples (enrichies)
- Temps de génération par leçon ✅
- **Tokens utilisés/limite** (contrôle budget)
- **Score de lisibilité FK** (adaptation audience)
- Taille du contenu produit (mots/chars)
- **Taux de succès** génération (sans timeout/erreur)

---

## 🔒 Garde-fous (renforcés)
- Pas de secrets en dur (API key via .env) ✅
- **Timeout 15s implémenté** avec gestion d'erreurs
- **Hard stop à 2000 tokens** côté requête OpenAI
- **Validation Pydantic stricte** sur tous les inputs
- Messages d'erreur clairs si génération échoue ✅

---

## 📈 **Différenciation v0.1 (vs "ChatGPT wrapper")**

1. **Adaptation audience automatique** (enfant/lycéen/adulte)
2. **Score de lisibilité validé** (pas juste du texte brut)
3. **Structure pédagogique** (objectifs → plan → sections → synthèse)
4. **Contrôle budgétaire** strict (coûts maîtrisés)
5. **Idempotence** (même requête = même résultat)

---

## 📊 Changelog MVP

- **v0.1.1 (2025-09-14)** : Focus qualité contenu, quiz déplacé v0.2, ajout métriques FK obligatoires, limites tokens/inputs strictes
- **v0.1.0 (2025-09-11)** : Version initiale MVP b