#!/usr/bin/env python3
# file: scripts/update_status.py
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple


def read_file(path: str) -> str:
    """Lit un fichier et retourne son contenu, ou chaîne vide si inexistant."""
    p = Path(path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def list_tree(root: Path) -> list[str]:
    """Liste tous les fichiers du projet (sauf .git)."""
    return [
        str(p).replace("\\", "/")
        for p in root.rglob("*")
        if p.is_file() and ".git/" not in str(p)
    ]


def extract_mvp_musts(mvp_md: str, limit: int = 12) -> List[str]:
    """Extrait les items Must du fichier MVP.md."""
    if not mvp_md:
        return []
    
    # Chercher section Must (plusieurs patterns possibles)
    patterns = [
        r"(?s)##+\s*✅?\s*Must.*?(?:\n##+|\Z)",
        r"(?s)###\s*Must.*?(?:\n###|\Z)",
        r"(?s)Must\s*\(.*?\).*?(?:\n###|\Z)"
    ]
    
    block = ""
    for pattern in patterns:
        m = re.search(pattern, mvp_md, flags=re.I)
        if m:
            block = m.group(0)
            break
    
    if not block:
        return []
    
    items: list[str] = []
    for line in block.splitlines():
        raw = line.strip()
        if not raw or raw.lower().startswith(("###", "##", "must")):
            continue
        item = raw.lstrip("-*•[] ").strip()
        if item and not item.startswith(("(", "Should", "Could", "Won't")):
            items.append(item)
    
    # Déduplication et limite
    seen: set[str] = set()
    deduped: list[str] = []
    for it in items:
        if it not in seen:
            seen.add(it)
            deduped.append(it)
    
    return deduped[:limit]


def analyze_file_content(filepath: str) -> Dict[str, any]:
    """Analyse le contenu d'un fichier pour détecter l'implémentation."""
    content = read_file(filepath)
    
    if not content:
        return {"exists": False, "empty": True, "lines": 0, "has_implementation": False}
    
    # Nettoyer le contenu (enlever commentaires et espaces)
    clean_lines = [
        line.strip() 
        for line in content.splitlines() 
        if line.strip() and not line.strip().startswith("#")
    ]
    
    has_implementation = len(clean_lines) > 0
    
    return {
        "exists": True,
        "empty": len(clean_lines) == 0,
        "lines": len(clean_lines),
        "has_implementation": has_implementation,
        "content_sample": content[:100] if content else ""
    }


def detect_storage_status(repo_files: list[str]) -> Tuple[str, str]:
    """Détecte le statut réel du storage SQLite."""
    storage_files = [f for f in repo_files if f.startswith("storage/") and f.endswith(".py")]
    
    if not storage_files:
        return "❌", "Aucun fichier storage/"
    
    # Analyser les fichiers critiques
    base_analysis = analyze_file_content("storage/base.py")
    models_analysis = analyze_file_content("storage/models.py")
    
    if not base_analysis["has_implementation"] and not models_analysis["has_implementation"]:
        return "🔄", "Structure présente mais fichiers vides"
    
    if base_analysis["has_implementation"] and models_analysis["has_implementation"]:
        return "✅", "Base et modèles implémentés"
    
    if base_analysis["has_implementation"]:
        return "🔄", "Base configurée, modèles manquants"
    
    if models_analysis["has_implementation"]:
        return "🔄", "Modèles définis, base manquante"
    
    return "🔄", "Implémentation partielle"


def detect_endpoints(repo_files: list[str]) -> List[str]:
    """Détecte les endpoints disponibles avec plus de précision."""
    endpoints: list[str] = []
    
    # Health endpoint
    if "api/routes/health.py" in repo_files:
        health_content = read_file("api/routes/health.py")
        if "@router.get" in health_content and "/health" in health_content:
            endpoints.append("GET /v1/health ✅")
    
    # Lessons endpoints
    lessons_files = [f for f in repo_files if "lesson" in f.lower() and "routes" in f and f.endswith(".py")]
    if lessons_files:
        for file in lessons_files:
            content = read_file(file)
            if "POST" in content and "/lessons" in content:
                endpoints.append("POST /v1/lessons 🔄")
            if "GET" in content and "/lessons/{" in content:
                endpoints.append("GET /v1/lessons/{id} 🔄")
    
    return endpoints if endpoints else ["Seul health endpoint détecté"]


def detect_must_status(mvp_musts: list[str], repo_files: list[str]) -> List[str]:
    """Détecte le statut réel de chaque Must avec granularité."""
    must_status = []
    
    for must in mvp_musts:
        status = "❌"  # Par défaut
        
        if "fastapi" in must.lower() and "health" in must.lower():
            if "api/main.py" in repo_files and "api/routes/health.py" in repo_files:
                health_content = read_file("api/routes/health.py")
                if "@router.get" in health_content:
                    status = "✅"
                else:
                    status = "🔄"
        
        elif "post" in must.lower() and "lessons" in must.lower():
            lessons_routes = [f for f in repo_files if "lesson" in f and "routes" in f]
            if lessons_routes:
                status = "🔄"  # Structure présente
                for route_file in lessons_routes:
                    content = read_file(route_file)
                    if "POST" in content and "/lessons" in content and "@router.post" in content:
                        status = "✅"
                        break
        
        elif "sqlite" in must.lower():
            storage_status, _ = detect_storage_status(repo_files)
            status = storage_status
        
        elif "logs" in must.lower() or "logging" in must.lower():
            # Chercher imports de logging dans les fichiers principaux
            main_files = ["api/main.py", "api/routes/health.py"]
            for file in main_files:
                content = read_file(file)
                if "import logging" in content or "from logging" in content:
                    status = "🔄"
                if "logger." in content or "log." in content:
                    status = "✅"
                    break
        
        elif "tests" in must.lower():
            test_files = [f for f in repo_files if f.startswith("tests/") and f.endswith(".py")]
            if "tests/test_health.py" in repo_files:
                if any("lesson" in f for f in test_files):
                    status = "✅"  # Happy path lessons testé
                else:
                    status = "🔄"  # Seulement health testé
        
        # Formatage avec icône
        icon = "✅" if status == "✅" else "🔄" if status == "🔄" else " "
        must_status.append(f"- [{icon}] {must}")
    
    return must_status


def detect_next_steps(repo_files: list[str], mvp_musts: list[str]) -> List[str]:
    """Suggère les prochaines étapes logiques basées sur l'état actuel."""
    next_steps = []
    
    # Analyser ce qui manque
    storage_status, _ = detect_storage_status(repo_files)
    has_lessons_route = any("lesson" in f and "routes" in f for f in repo_files)
    has_lessons_test = any("lesson" in f for f in repo_files if f.startswith("tests/"))
    
    # Priorités logiques
    if storage_status == "🔄":
        next_steps.append("1. **Implémenter storage layer** - SQLAlchemy base + models Lesson")
    elif storage_status == "❌":
        next_steps.append("1. **Créer storage complet** - Configuration SQLite + modèles")
    
    if not has_lessons_route:
        next_steps.append("2. **Créer endpoint POST /v1/lessons** - Route + DTO + orchestration")
    
    if not has_lessons_test:
        next_steps.append("3. **Tests e2e lessons** - Happy path + validation + idempotence")
    
    # Logging si pas implémenté
    main_content = read_file("api/main.py")
    if "logging" not in main_content:
        next_steps.append("4. **Ajouter logging structuré** - run_id + métriques basiques")
    
    return next_steps[:3]  # Max 3 étapes pour rester focalisé


def generate_progress_summary(repo_files: list[str]) -> Dict[str, any]:
    """Génère un résumé du progrès global."""
    storage_status, storage_detail = detect_storage_status(repo_files)
    endpoints = detect_endpoints(repo_files)
    
    # Calcul du pourcentage MVP
    essentials = {
        "fastapi": "api/main.py" in repo_files,
        "health": "api/routes/health.py" in repo_files,
        "storage": storage_status == "✅",
        "tests": "tests/test_health.py" in repo_files,
        "lessons_route": any("lesson" in f and "routes" in f for f in repo_files)
    }
    
    completed = sum(1 for v in essentials.values() if v)
    total = len(essentials)
    progress_pct = int((completed / total) * 100)
    
    return {
        "progress_pct": progress_pct,
        "completed": completed,
        "total": total,
        "storage_detail": storage_detail,
        "endpoints_count": len([e for e in endpoints if "✅" in e]),
        "phase": "Setup" if progress_pct < 40 else "Development" if progress_pct < 80 else "Testing"
    }


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

    # Analyses avancées
    storage_status, storage_detail = detect_storage_status(repo_files)
    endpoints = detect_endpoints(repo_files)
    
    essentials = {
        "fastapi": "✅" if "api/main.py" in repo_files else "❌",
        "health": "✅" if "api/routes/health.py" in repo_files else "❌",
        "storage": storage_status,
        "tests": "✅" if "tests/test_health.py" in repo_files else "❌",
    }

    # Must avec statuts granulaires
    musts = extract_mvp_musts(mvp_md) or [
        "FastAPI en place avec health check",
        "POST /v1/lessons qui génère une leçon complète (plan + texte)",
        "SQLite pour stocker les leçons",
        "Logs simples (INFO)",
        "Tests : health + happy path",
    ]
    musts_with_status = detect_must_status(musts, repo_files)
    
    # Prochaines étapes et résumé
    next_steps = detect_next_steps(repo_files, musts)
    progress = generate_progress_summary(repo_files)

    # Endpoints formatés
    if endpoints:
        endpoints_md = "\n".join(f"- {e}" for e in endpoints)
    else:
        endpoints_md = "_Aucun détecté (voir README/api)._"

    # Next steps formatés
    next_steps_md = "\n".join(next_steps) if next_steps else "_Toutes les étapes MVP sont complètes! 🎉_"

    # Lien CI
    run_link = ""
    server = os.getenv("GITHUB_SERVER_URL")
    repo = os.getenv("GITHUB_REPOSITORY")
    run_id = os.getenv("GITHUB_RUN_ID")
    if server and repo and run_id:
        run_link = f"  \n**CI Run**: {server}/{repo}/actions/runs/{run_id}"

    py_version = sys.version.split()[0]

    status_md = f"""# Project Status — Skillence AI

**Date (UTC)**: {args.date}
**Commit**: `{args.commit}` — {args.message}
**Python**: {py_version}{run_link}

## 📊 Progress Overview
**Phase**: {progress['phase']} | **MVP Progress**: {progress['progress_pct']}% ({progress['completed']}/{progress['total']})

## 🔧 Build & Tests
- Tests: {tests_status}

## ⚙️ Essentials (MVP Components)
- FastAPI present: {essentials['fastapi']}
- Health endpoint: {essentials['health']}
- SQLite storage: {storage_status} _{storage_detail}_
- Tests directory: {essentials['tests']}

## 🌐 Endpoints Status
{endpoints_md}

## ✅ MVP Musts Progress
{chr(10).join(musts_with_status)}

## 🚀 Next Steps (Agent Priority)
{next_steps_md}

## 📝 Notes
- **Storage detail**: {storage_detail}
- **For GPT agents**: This status provides current implementation state for context-aware code generation
- Auto-generated by GitHub Actions (`.github/workflows/status.yml`)

## 🔗 References
- [README.md](README.md) — Quick Start & API Usage
- [MVP.md](MVP.md) — MVP scope and constraints  
- [skillence_agent_kit.md](skillence_agent_kit.md) — Long-term vision and architecture
"""

    Path("STATUS.md").write_text(status_md, encoding="utf-8")
    print(f"✅ STATUS.md generated - Progress: {progress['progress_pct']}% | Phase: {progress['phase']}")


if __name__ == "__main__":
    main()