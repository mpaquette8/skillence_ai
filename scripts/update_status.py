#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List


def read_file(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def list_tree(root: Path) -> list[str]:
    return [
        str(p).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and ".git/" not in str(p)
    ]


def extract_mvp_musts(mvp_md: str, limit: int = 12) -> List[str]:
    """
    Récupère la liste 'Must' depuis MVP.md (heuristique simple et robuste).
    """
    if not mvp_md:
        return []
    m = re.search(r"(?s)##+\s*✅?\s*Must.*?(?:\n##+|\Z)", mvp_md, flags=re.I)
    if not m:
        m = re.search(r"(?s)###\s*Must.*?(?:\n###|\Z)", mvp_md, flags=re.I)
    if not m:
        return []
    block = m.group(0)
    items: list[str] = []
    for line in block.splitlines():
        raw = line.strip()
        if not raw or raw.lower().startswith(("###", "##")):
            continue
        item = raw.lstrip("-*•[] ").strip()
        if item:
            items.append(item)
    # de-dupe, garde l'ordre
    seen = set()
    deduped: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            deduped.append(it)
    return deduped[:limit]


def detect_simple_endpoints(repo_files: list[str]) -> list[str]:
    """
    Détection ultra-simple des endpoints connus via inspection des chemins.
    Ne remplace pas une introspection FastAPI, mais donne un signal utile.
    """
    endpoints: list[str] = []
    # indices basés sur le MVP
    if any(f.endswith("api/routes/health.py") for f in repo_files) or any("GET /v1/health" in f for f in repo_files):
        endpoints.append("GET /v1/health")
    # hueristiques courantes
    if any("lessons" in f and f.endswith(".py") and "/api/" in f for f in repo_files):
        # on liste les 2 principaux du MVP
        endpoints.extend(["POST /v1/lessons", "GET /v1/lessons/{id}"])
    # dédup
    endpoints = list(dict.fromkeys(endpoints))
    return endpoints


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", required=True)
    ap.add_argument("--message", required=True)
    ap.add_argument("--date", required=True)
    ap.add_argument("--tests_failed", default="False")
    args = ap.parse_args()

    repo_files = list_tree(Path("."))
    readme = read_file("README.md")
    mvp_md = read_file("MVP.md")
    kit = read_file("skillence_agent_kit.md")

    tests_failed = str(args.tests_failed).lower() in {"1", "true", "yes"}
    tests_status = "❌ FAIL" if tests_failed else "✅ PASS"

    essentials = {
        "fastapi": "✅" if "api/main.py" in repo_files else "❌",
        "health": "✅" if ("GET /v1/health" in readme or "api/routes/health.py" in repo_files) else "❌",
        "sqlite": "✅" if any(f.startswith("storage/") for f in repo_files) else "❌",
        "tests": "✅" if any(f.startswith("tests/") for f in repo_files) else "❌",
    }

    # Musts du MVP
    musts = extract_mvp_musts(mvp_md) or [
        "FastAPI en place avec health check",
        "POST /v1/lessons qui génère une leçon complète (plan + texte)",
        "SQLite pour stocker les leçons",
        "Logs simples (INFO)",
        "Tests : health + happy path",
    ]

    # Endpoints détectés (heuristique)
    endpoints = detect_simple_endpoints(repo_files)
    if not endpoints and "GET /v1/health" in readme:
        endpoints.append("GET /v1/health")

    # Infos CI (liens utiles si exécuté dans GitHub Actions)
    run_link = ""
    server = os.getenv("GITHUB_SERVER_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if server and repo and run_id:
        run_link = f"{server}/{repo}/actions/runs/{run_id}"

    py_version = sys.version.split()[0]

    status_md = f"""# Project Status — Skillence AI

**Date (UTC)**: {args.date}
**Commit**: `{args.commit}` — {args.message}
**Python**: {py_version}{("  \n**CI Run**: " + run_link) if run_link else ""}

## Build & Tests
- Tests: {tests_status}

## Essentials (MVP)
- FastAPI present: {essentials['fastapi']}
- Health endpoint: {essentials['health']}
- SQLite storage present: {essentials['sqlite']}
- Tests directory present: {essentials['tests']}

## Endpoints détectés (heuristique)
{("- " + chr(10) .join(f"- {e}" for e in endpoints)) if endpoints else "_Aucun détecté (voir README/api)._"}
 
## MVP Musts Snapshot
{chr(10).join(f"- [ ] {m}" for m in musts)}

## Notes
- Les Musts sont détectés automatiquement depuis `MVP.md` si présent.
- Ce fichier est généré par GitHub Actions (`.github/workflows/status.yml`).

## Links
- README.md — Quick Start & Endpoints
- MVP.md — MVP scope and constraints
- skillence_agent_kit.md — long-term vision and constraints
"""
    Path("STATUS.md").write_text(status_md, encoding="utf-8")


if __name__ == "__main__":
    main()
