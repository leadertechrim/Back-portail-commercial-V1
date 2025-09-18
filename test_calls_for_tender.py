#!/usr/bin/env python3
"""
Script de test pour les routes des appels d'offres
"""

import requests
import json
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"  # Changez pour Railway si nécessaire
# BASE_URL = "https://applesoffres-production.up.railway.app"  # Pour Railway

def test_calls_for_tender():
    """Tester les routes des appels d'offres"""
    
    print("🧪 Test des routes des appels d'offres")
    print("=" * 50)
    
    # 1. Test GET - Récupérer tous les appels d'offres
    print("\n1️⃣ Test GET /api/calls-for-tender")
    try:
        response = requests.get(f"{BASE_URL}/api/calls-for-tender")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Récupéré {len(data)} appels d'offres")
            if data:
                print(f"Premier appel: {data[0].get('title', 'N/A')}")
        else:
            print(f"❌ Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # 2. Test POST - Créer un appel d'offres (nécessite authentification admin)
    print("\n2️⃣ Test POST /api/calls-for-tender (nécessite auth admin)")
    try:
        # D'abord, se connecter pour obtenir un token
        login_data = {
            "email": "admin@example.com",
            "password": "admin123"
        }
        
        login_response = requests.post(f"{BASE_URL}/api/login", json=login_data)
        if login_response.status_code == 200:
            token = login_response.json().get("token")
            print(f"✅ Token obtenu: {token[:20]}...")
            
            # Maintenant créer un appel d'offres
            call_data = {
                "title": "Test Appel d'Offres",
                "source": "Test Source",
                "client": "Test Client",
                "state": "En cours",
                "description": "Description de test",
                "deadline": (datetime.now() + timedelta(days=30)).isoformat()
            }
            
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(f"{BASE_URL}/api/calls-for-tender", 
                                   data=call_data, headers=headers)
            print(f"Status: {response.status_code}")
            if response.status_code == 201:
                data = response.json()
                print(f"✅ Appel d'offres créé: {data.get('call', {}).get('_id')}")
                call_id = data.get('call', {}).get('_id')
                
                # 3. Test PUT - Modifier l'appel d'offres
                print("\n3️⃣ Test PUT /api/calls-for-tender/<id>")
                update_data = {
                    "title": "Test Appel d'Offres Modifié",
                    "source": "Test Source Modifiée",
                    "client": "Test Client Modifié",
                    "state": "Terminé",
                    "description": "Description modifiée",
                    "deadline": (datetime.now() + timedelta(days=15)).isoformat()
                }
                
                response = requests.put(f"{BASE_URL}/api/calls-for-tender/{call_id}", 
                                      data=update_data, headers=headers)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ Appel d'offres modifié avec succès")
                else:
                    print(f"❌ Erreur modification: {response.text}")
                
                # 4. Test DELETE - Supprimer l'appel d'offres
                print("\n4️⃣ Test DELETE /api/calls-for-tender/<id>")
                response = requests.delete(f"{BASE_URL}/api/calls-for-tender/{call_id}", 
                                        headers=headers)
                print(f"Status: {response.status_code}")
                if response.status_code == 200:
                    print("✅ Appel d'offres supprimé avec succès")
                else:
                    print(f"❌ Erreur suppression: {response.text}")
                
            else:
                print(f"❌ Erreur création: {response.text}")
        else:
            print(f"❌ Impossible de se connecter: {login_response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")
    
    # 5. Test sans authentification (devrait fonctionner avec @optional_auth)
    print("\n5️⃣ Test GET sans authentification")
    try:
        response = requests.get(f"{BASE_URL}/api/calls-for-tender")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Accès public autorisé")
        else:
            print(f"❌ Accès public refusé: {response.text}")
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_debug():
    """Tester la route de debug"""
    print("\n🔍 Test route de debug")
    print("=" * 30)
    
    try:
        response = requests.get(f"{BASE_URL}/api/debug")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("✅ Debug info:")
            print(f"  - MongoDB: {data.get('mongo_status')}")
            print(f"  - Users: {data.get('users_status')}")
            print(f"  - Sources: {data.get('sources_status')}")
        else:
            print(f"❌ Erreur debug: {response.text}")
    except Exception as e:
        print(f"❌ Exception debug: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage des tests")
    test_debug()
    test_calls_for_tender()
    print("\n✅ Tests terminés")

