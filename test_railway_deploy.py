#!/usr/bin/env python3
"""
Test rapide pour vérifier le déploiement Railway
"""

import requests

RAILWAY_URL = "https://applesoffres-production.up.railway.app"

def test_railway():
    print("🚀 Test du déploiement Railway")
    print("=" * 40)
    
    # Test 1: API de base
    print("\n1. Test API de base...")
    try:
        response = requests.get(f"{RAILWAY_URL}/api/test")
        if response.status_code == 200:
            print("✅ API fonctionne")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"❌ Erreur: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 2: Debug info
    print("\n2. Test debug info...")
    try:
        response = requests.get(f"{RAILWAY_URL}/api/debug")
        if response.status_code == 200:
            print("✅ Debug OK")
            data = response.json()
            print(f"   MongoDB: {data.get('mongo_status')}")
            print(f"   Utilisateurs: {data.get('users_status')}")
            print(f"   Sources: {data.get('sources_status')}")
        else:
            print(f"❌ Erreur: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 3: Utilisateurs publics
    print("\n3. Test utilisateurs publics...")
    try:
        response = requests.get(f"{RAILWAY_URL}/api/users-public")
        if response.status_code == 200:
            print("✅ Utilisateurs publics OK")
            data = response.json()
            print(f"   Nombre d'utilisateurs: {data.get('count', 0)}")
            if data.get('users'):
                for user in data['users'][:3]:  # Afficher les 3 premiers
                    print(f"   - {user.get('name', 'N/A')} ({user.get('email')})")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   Réponse: {response.text}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    # Test 4: Inscription
    print("\n4. Test inscription...")
    try:
        user_data = {
            "email": "test@railway.com",
            "password": "test123",
            "name": "Test Railway",
            "role": "user"
        }
        response = requests.post(f"{RAILWAY_URL}/register", json=user_data)
        if response.status_code == 201:
            print("✅ Inscription OK")
        elif response.status_code == 400 and "déjà existant" in response.json().get("message", ""):
            print("✅ Utilisateur existe déjà")
        else:
            print(f"❌ Erreur: {response.status_code}")
            print(f"   Réponse: {response.json()}")
    except Exception as e:
        print(f"❌ Erreur: {e}")
    
    print("\n" + "=" * 40)
    print("🎯 Test terminé!")

if __name__ == "__main__":
    test_railway()
