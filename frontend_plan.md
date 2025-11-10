# Frontend v0.2 — Préparation

## 🎯 Objectifs MVP élargis
- Offrir une interface web minimale pour initier une génération de leçon et consulter l’historique stocké (tables `requests` / `lessons`).
- Permettre une authentification simple par e-mail (passwordless ou mot de passe minimal) et un second canal OAuth Google.
- Rester aligné sur la philosophie KISS : réutiliser FastAPI, éviter d’introduire un second framework serveur.

## 📦 Périmètre fonctionnel
| Feature | Description | Notes KISS |
|---------|-------------|------------|
| Auth e-mail | Formulaire de connexion/inscription simple. | Passwordless (lien magique) recommandé pour limiter la gestion des mots de passe. |
| Auth Google | Bouton « Se connecter avec Google » via OAuth (Authlib ou external IdP). | Décider si on externalise (Auth0) ou si on gère en direct avec Google OAuth. |
| Tableau de bord | Liste des leçons enregistrées (titre, audience, date). | Paginer côté client simplement (HTMX ou requête fetch). |
| Fiche de leçon | Vue détaillée Markdown + métriques de lisibilité. | Rendu Markdown côté client (Marked.js) ou serveur (Jinja2 + Markdown). |
| Génération | Formulaire sujet/audience/durée. | Appel direct au backend existant `/v1/lessons`. |

## 🛠️ Choix techniques proposés
- **Frontend** : pages server-side rendues par FastAPI + Jinja2 + HTMX (pas de framework SPA complet).
- **Authentification** : 
  - Passwordless e-mail via envoi de lien signé (itsdangerous déjà dispo dans stdlib? sinon `itsdangerous` léger).
  - OAuth Google via `authlib` (dépendance raisonnable) ou service externe type Auth0 (si clé/config déjà prévue).
- **Styles** : Tailwind CDN (pas de build step) ou simple CSS utilitaire.
- **State** : session HTTP signée (FastAPI `SessionMiddleware`) + cookie.
- **API calls** : HTMX ou fetch JSON -> mise à jour partielle des templates pour rester simple.

## 🧱 Pré-requis backend
1. Ajouter modèles `users` et `sessions` (SQLite).
2. Exposer endpoints auth (login email, callback Google, logout).
3. Brancher les vues les plus simples (HTML) sur FastAPI (router `/web`).
4. Ajouter middleware session/cookies et CSRF minimal (token simple dans formulaire).
5. Étendre tests (pytest + httpx) pour les routes HTML critiques (auth happy path + accès protégé).

## 🗺️ Roadmap proposée
1. **Semaine 1** — Auth simple
   - Modèles `users` / `login_tokens`.
   - Formulaire e-mail + envoi lien (mockable en dev).
   - Middleware session + tests (connexion/déconnexion).
2. **Semaine 2** — UI cours
   - Page dashboard (liste) � todo: appel GET /v1/lessons + rendu Markdown.
   - Vue détail Markdown (conversion côté serveur).
   - Formulaire génération + feedback état.
3. **Semaine 3** — OAuth & polish
   - Intégration Google OAuth (Authlib).
   - Protection routes (redirect si non connecté).
   - Styling léger + textes pédagogiques.
   - Tests d’intégration (connexion Google mockée, génération via UI).

## ⚠️ Risques & mitigations
- **Complexité auth** : passwordless limite la gestion des mots de passe mais exige un canal e-mail fiable (prévoir fallback console en dev).
- **Consentement OAuth** : besoin de config projet Google, logs d’erreurs clairs pour onboarding.
- **Stockage sessions** : cookie signé + TTL. Sur SQLite, attention aux verrous — maintenir la simplicité.
- **Double surface API/UI** : garder la logique métier centralisée dans `api/services/lessons.py`; les vues HTML ne doivent être que des clients.

## ✅ Checklist démarrage
- [ ] Valider la stratégie (passwordless + Google) avec le PO.
- [ ] Créer un espace `web/` pour routes/templates/tests front.
- [ ] Mettre en place l’envoi mail « dev » (console/log) avant production.
- [ ] Documenter dans README la pile front et commandes.
- [ ] Mettre à jour AGENTS.md si besoin pour refléter la nouvelle surface.

