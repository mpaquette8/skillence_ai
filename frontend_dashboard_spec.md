# Frontend Web — Dashboard & Génération (Draft)

## 🎯 Objectifs
- Afficher, côté `/web/dashboard`, la liste des leçons déjà stockées (titre, audience, date).
- Proposer un formulaire pour déclencher une nouvelle génération (subject/audience/duration) depuis l’UI.
- Toujours respecter l’approche KISS (HTML minimal rendu serveur, pas de framework JS lourd).

## 📋 Exigences fonctionnelles
1. **Liste des leçons**
   - Afficher uniquement les 10 dernières (ordre décroissant par `created_at`).
   - Chaque élément : titre, audience, date (format court) + lien vers `/web/lessons/{id}` (page à créer).
2. **Formulaire de génération**
   - Champs : `subject` (text), `audience` (select), `duration` (select).
   - Validation simple côté serveur (pour réutiliser `LessonRequest`).
   - À la soumission :
     - Appeler l’API existante (POST `/v1/lessons`) via HTTP interne (`httpx` synchronisé).
     - Si succès : affichage message + rafraîchissement de la liste.
     - Si erreur : message d’erreur clairement visible.
3. **Page détail `/web/lessons/{id}`**
   - Montrer le Markdown rendu (utiliser `markdown` en python ou afficher brut avec `<pre>` pour MVP).
   - Rappeler les métriques `quality` (score FK, message).

## 🔌 Architecture proposée (KISS)
- `web/routes.py`
  - Ajouter route `GET /web/dashboard` qui :
    - Vérifie session (déjà fait).
    - Récupère les leçons via `storage` (joint Lesson/Request) plutôt que re-appeler l’API.
  - Ajouter `POST /web/dashboard` pour traiter le formulaire :
    - Valide inputs.
    - Appelle `create_lesson()` via le service Python (évite requête HTTP, plus simple) **ou** via `api.services.lessons.create_lesson`.
    - Redirige (pattern Post/Redirect/Get) ou renvoie la page avec message.
  - Ajouter `GET /web/lessons/{lesson_id}`.
- **Templates** (HTML inline ou string). Pour KISS, garder HTML inline (pas de moteur template pour l’instant).

## 🧪 Tests à prévoir
1. `GET /web/dashboard` auth + base vide → message “Aucune leçon”.
2. `POST /web/dashboard` avec sujet valide → simulate `create_lesson` (patch) et vérifier redirection/message.
3. `GET /web/lessons/{id}` existant → 200 + contenu.
4. `GET /web/lessons/{id}` inexistant → 404.

## ⚙️ Tâches concrètes
- Étendre `web/routes.py` :
  1. Ajouter `require_session(request)` (Retourne email + session_id).
  2. `GET /web/dashboard` : charge les 10 dernières leçons (`Lesson` + `Request`).
  3. `POST /web/dashboard` : lit formulaire, appelle `create_lesson` (service Python), redirige avec message.
  4. `GET /web/lessons/{lesson_id}` : affiche markdown brut + métriques.
- Créer `tests/test_web_dashboard.py` :
  1. Fixture DB isolée (reprendre pattern `web_app_with_isolated_db`).
  2. Test empty state + après insertion (liste 10 dernières).
  3. Test `POST` (patch `api.services.lessons.create_lesson`).
  4. Test détail / 404.
- Ajouter helper(s) rendu HTML (string) directement dans `web/routes.py` (KISS).
- Rendu contenu : utiliser `<pre>` pour le markdown (pas de dépendances nouvelles).

## 📝 Notes
- Rester “formulaire simple” (pas de HTMX pour l’instant).
- Les routes doivent renvoyer des `HTMLResponse`.
- Penser à la pagination/minimum (10 leçons). Liste plus longue → option “voir plus tard”.
