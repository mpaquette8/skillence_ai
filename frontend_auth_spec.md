# Frontend Auth — Spécification v0.2 (Draft)

## 🎯 Objectifs
- Authentifier un utilisateur via lien magique e-mail (passwordless) + option Google OAuth.
- Restreindre l’accès aux pages HTML (`/web/*`) aux utilisateurs connectés.
- S’intégrer sans perturber les endpoints REST existants (`/v1/*`).

## 📦 Modèles SQLite à ajouter
| Table | Champs | Notes |
|-------|--------|-------|
| `users` | `id` (UUID), `email` (unique, lower-case), `google_sub` (nullable), `created_at` | Google et e-mail partagent la même table. |
| `login_tokens` | `id` (UUID), `user_id`, `token` (32 chars), `expires_at`, `redeemed_at` | Lien magique signé. Index sur `token`. TTL 15 min. |
| `sessions` | `id` (UUID), `user_id`, `issued_at`, `expires_at`, `ip`, `user_agent_hash` | Stocke les sessions actives par cookie. |

Migration: étendre `storage/models.py` en gardant ≤150 lignes (classes `User`, `LoginToken`, `Session`). Ajouter tests ORM dédiés.

## 🔌 Endpoints à créer
| Méthode/Route | Description | Auth requise |
|---------------|-------------|--------------|
| `GET /web/login` | Formulaire e-mail + bouton Google. | Non |
| `POST /web/login` | Soumet e-mail, génère token & envoie mail (console en dev). | Non |
| `GET /web/login/callback` | Consomme token, crée session, redirige `/web/dashboard`. | Non |
| `GET /web/login/google` | Redirection vers Google OAuth. | Non |
| `GET /web/login/google/callback` | Finalise OAuth (Authlib), crée/associe user, session. | Non |
| `POST /web/logout` | Révoque session courante. | Oui |
| `GET /web/dashboard` | Liste des leçons (pagination simple). | Oui |
| `GET /web/lessons/{id}` | Vue Markdown + métriques. | Oui |
| `POST /web/lessons` | Soumission formulaire; appelle `/v1/lessons`. | Oui |

## 🔑 Gestion des sessions
- Cookie `skillence_session` (Secure+HttpOnly, 24h).
- Contenu: UUID session stocké en DB ; pas de JWT.
- Middleware FastAPI (`SessionMiddleware` + wrapper maison) pour charger l’utilisateur (request.state.user).

## ✉️ Lien magique (passwordless)
1. Utilisateur saisit e-mail → `POST /web/login`.
2. Générer `token` random + entrée `login_tokens`.
3. Envoyer URL `https://app/…/callback?token=...`. En dev: log console.
4. Callback valide le token (non expiré & non consommé) → crée session → redirige.
5. Nettoyage: marquer `redeemed_at`. CRON futur (non MVP) pour purger expirés.

## 🌐 Google OAuth (optionnel v0.2)
- Utiliser `Authlib` (dépendance unique).
- Enregistrer client ID/secret via `.env`.
- Si `google_sub` inconnu → créer user ; sinon reuse.
- Gestion erreurs: message clair (quota, refus).

## 🧪 Tests requis (pytest + httpx)
1. `POST /web/login` → crée token / log email (mock).
2. `GET /web/login/callback?token=...` happy path → cookie session.
3. Token expiré ou déjà utilisé → HTTP 400.
4. Accès `/web/dashboard` non authentifié → 303 vers `/web/login`.
5. `POST /web/lessons` authentifié → appelle `create_lesson` (mock) & affiche message succès.
6. Google OAuth mocké (Authlib client patch) → callback crée session.

## 📁 Organisation recommandée
```
web/
  routes.py          # APIRouter HTML
  templates/
    login.html
    dashboard.html
    lesson_detail.html
    base.html
  forms.py (option)  # helpers validation simple
tests/
  test_web_auth.py
  test_web_lessons.py
```

## ⚠️ To-do avant exécution
- Décider fournisseur mail (console pour MVP, SMTP plus tard).
- Ajouter clés `.env`: `SESSION_SECRET`, `OAUTH_GOOGLE_CLIENT_ID/SECRET`.
- Mettre à jour `README.md` + `AGENTS.md` pour refléter la nouvelle surface web.
- Préparer rétro-compatibilité si `skillence_ai.db` déjà en prod (migration manuelle).

## ✅ Validation & prochaines étapes
1. **Validation produit/tech**  
   - Revue du présent document avec PO + tech lead.  
   - Vérifier que passwordless + Google répondent bien au besoin utilisateur.

2. **Planification migration DB**
   - Étendre `storage/models.py` avec `User`, `LoginToken`, `Session` (≲80 lignes).  
   - Créer un script de migration léger (`python scripts/init_users_tables.py`) ou décrire procédure manuelle (recréation SQLite).  
   - Mettre à jour `tests/test_storage.py` pour couvrir la création et la suppression en cascade des nouvelles tables.  
   - Documenter dans `README.md` comment régénérer la base (`alembic` non requis pour MVP).

3. **3. **Vertical slice �lien magique�** *(livr� v0.2.0)*
   - Ajouter un routeur `web/routes.py` avec `GET/POST /web/login` et `GET /web/login/callback`.  
   - Créer templates `templates/base.html`, `templates/login.html`.  
   - Implémenter service `send_magic_link_email(email, token)` logguant l’URL en dev.  
   - Stocker les sessions en DB + cookie `skillence_session`.  
   - Couvrir avec `tests/test_web_auth.py` : génération token, callback valide, token expiré.  
   - Mettre à jour `README.md` (section “Interface web”).
