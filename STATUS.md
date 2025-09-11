# Project Status — Skillence AI

**Date (UTC)**: 2025-09-11T18:22:16Z
**Commit**: `b06c26c` — ci: add auto-updated STATUS.md via GitHub Actions

## Build & Tests
- Tests: ❌ FAIL

## Essentials (MVP)
- FastAPI present: ✅
- Health endpoint: ✅
- SQLite storage present: ✅
- Tests directory present: ✅

## MVP Musts Snapshot
- [ ] FastAPI en place avec health check
- [ ] POST /v1/lessons qui génère une leçon complète (plan + texte)
- [ ] SQLite pour stocker les leçons
- [ ] Logs simples (INFO)
- [ ] Tests : health + happy path

## Notes
- Les Musts sont détectés automatiquement depuis `MVP.md` si présent.
- Ce fichier est généré par GitHub Actions (`.github/workflows/status.yml`).

## Links
- README.md — Quick Start & Endpoints
- MVP.md — MVP scope and constraints
- skillence_agent_kit.md — long-term vision and constraints
