# // file: migrate_no_quiz.py

"""
Script de migration pour supprimer les colonnes quiz (v0.1.1 → v0.1.2).
Usage: python migrate_no_quiz.py
"""

import os
import shutil
from pathlib import Path

def migrate_database():
    """
    Migration simple : supprime la DB existante pour recréer le schéma.
    Approche MVP : pas de migration complexe, juste reset.
    """
    db_files = [
        "skillence_ai.db",
        "test.db", 
        "app.db"
    ]
    
    print("🔄 Migration v0.1.1 → v0.1.2 (suppression quiz)")
    
    for db_file in db_files:
        if os.path.exists(db_file):
            print(f"  📤 Suppression {db_file}")
            os.remove(db_file)
    
    print("✅ Migration terminée - les nouvelles tables seront créées au prochain démarrage")


def clean_test_artifacts():
    """Nettoie les artifacts de tests."""
    dirs_to_clean = [
        ".pytest_cache", 
        "__pycache__",
        "tests/__pycache__",
        "api/__pycache__",
        "agents/__pycache__",
        "storage/__pycache__"
    ]
    
    for dir_path in dirs_to_clean:
        if os.path.exists(dir_path):
            print(f"  🧹 Nettoyage {dir_path}")
            shutil.rmtree(dir_path, ignore_errors=True)


if __name__ == "__main__":
    migrate_database()
    clean_test_artifacts()
    
    print("\n🎯 Prochaines étapes:")
    print("1. pytest -v  # Vérifier que tous les tests passent")
    print("2. uvicorn api.main:app --reload  # Démarrer le serveur")
    print("3. curl http://localhost:8000/v1/health  # Test rapide")


# // file: test_manual.py

"""
Script de test manuel rapide pour vérifier le nettoyage quiz.
Usage: python test_manual.py
"""

import json
import requests
import time

def test_lesson_creation():
    """Test rapide de création de leçon sans quiz."""
    
    print("🧪 Test manuel - Création de leçon (SANS QUIZ)")
    
    # Payload de test
    payload = {
        "subject": "Les volcans",
        "audience": "enfant", 
        "duration": "short"
    }
    
    print(f"📤 Envoi: {json.dumps(payload, indent=2)}")
    
    try:
        # POST /v1/lessons
        start_time = time.time()
        resp = requests.post("http://localhost:8000/v1/lessons", 
                            json=payload, 
                            timeout=30)
        duration = time.time() - start_time
        
        print(f"⏱️  Durée: {duration:.2f}s")
        print(f"📥 Status: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            lesson_id = data["lesson_id"]
            print(f"✅ Leçon créée: {lesson_id}")
            print(f"   Titre: {data['title']}")
            print(f"   Cache: {data['from_cache']}")
            
            # GET détail
            detail_resp = requests.get(f"http://localhost:8000/v1/lessons/{lesson_id}")
            
            if detail_resp.status_code == 200:
                detail_data = detail_resp.json()
                print(f"📄 Contenu récupéré:")
                print(f"   Objectifs: {len(detail_data['objectives'])} items")
                print(f"   Plan: {len(detail_data['plan'])} sections") 
                print(f"   Contenu: {len(detail_data['content'])} caractères")
                
                # Vérification SANS quiz
                if "quiz" not in detail_data:
                    print("✅ Quiz correctement supprimé")
                else:
                    print(f"❌ Quiz encore présent: {detail_data['quiz']}")
                    
                # Aperçu du markdown
                preview = detail_data["content"][:200].replace('\n', ' ')
                print(f"   Aperçu: {preview}...")
                
            else:
                print(f"❌ Erreur GET: {detail_resp.status_code}")
                
        else:
            print(f"❌ Erreur POST: {resp.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Serveur non accessible - Lancez 'uvicorn api.main:app --reload'")
    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    test_lesson_creation()