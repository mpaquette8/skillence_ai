# Email Auth – Pistes d’intégration

## Option 1 — SMTP simple
- Utiliser un serveur SMTP (Gmail, Mailgun, serveur d’entreprise).
- Avantages : pas de dépendance tierce, coûts faibles.
- Contraintes :
  - Gérer la configuration (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM`).
  - Ajouter envoi synchrone via `smtplib` (ou `aiosmtplib` plus tard).
  - Gérer les quotas/limitations (CAPTCHA Gmail, etc.).
- Implémentation MVP :
  - Ajouter module `web/email.py` avec fonction `send_magic_link_email(email, url)`.
  - En dev : fallback console si variables manquantes.

## Option 2 — Provider SaaS (p.ex. Postmark, Mailgun API)
- Avantages : délivrabilité supérieure, gestion des logs e-mail, webhooks.
- Contraintes :
  - Clé API supplémentaire (`MAIL_PROVIDER_API_KEY`, `MAIL_PROVIDER_DOMAIN`).
  - Dépendance HTTP additionnelle (requests/httpx).
- Implémentation :
  - Wrapper simple (ex: `requests.post()` sur endpoint provider).
  - Gestion erreurs (retenter, log clair).

## Recommandation MVP
1. **Court terme (v0.2)** : ajout SMTP optionnel, avec fallback sur logs si non configuré.
   - Simplicité, pas de compte supplémentaire requis.
2. **Moyen terme** : prévoir un switchable provider via settings (`MAIL_TRANSPORT=smtp|provider|console`).
3. **Documentation** :
   - Mettre à jour README pour lister nouvelles variables.
   - Ajouter test d’intégration “mock envoyer mail” (patch `send_magic_link_email`).

## TODO associés
- [ ] Créer `web/email.py` et y déplacer `_send_magic_link`.
- [ ] Gérer chargement des settings (SMTP).
- [ ] Ajouter tests unitaires sur la fonction d’envoi (mock smtplib).
- [ ] Mettre à jour `frontend_auth_spec.md` avec la trajectoire choisie.
