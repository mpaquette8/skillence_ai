#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
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


def extract_mvp_musts(mvp_md: str) -> List[str]:
    """Very simple heuristic to pull the Must list from MVP.md."""
    if not mvp_md:
        return []
    m = re.search(r"###\s*Must.*?(?:###|\Z)", mvp_md, flags=re.S | re.I)
    if not m:
        return []
    block = m.group(0)
    items: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line or line.lower().startswith("###"):
            continue
        line = line.lstrip("-*• ").strip()
        if line:
            items.append(line)
    return items


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

    musts = extract_mvp_musts(mvp_md) or [
        "FastAPI en place avec health check",
        "POST /v1/lessons qui génère une leçon complète (plan + texte)",
        "SQLite pour stocker les leçons",
        "Logs simples (INFO)",
        "Tests : health + happy path",
    ]

    status_md = f"""# Project Status — Skillence AI

**Date (UTC)**: {args.date}
**Commit**: `{args.commit}` — {args.message}

## Build & Tests
- Tests: {tests_status}

## Essentials (MVP)
- FastAPI present: {essentials['fastapi']}
- Health endpoint: {essentials['health']}
- SQLite storage present: {essentials['sqlite']}
- Tests directory present: {essentials['tests']}

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
