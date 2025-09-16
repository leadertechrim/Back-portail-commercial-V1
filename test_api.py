#!/usr/bin/env python3
"""
Script de test pour l'API de gestion des utilisateurs
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_api():
    print("🧪 Test de l'API de gestion des utilisateurs")
    print("=" * 50)
    
    # Test 1: Vérifier que l'API fonctionne
    print("\n1. Test de l'API de base...")
    try:
        response = requests.get(f"{BASE_URL}/api/test")
        if response.status_code == 200:
            print("✅ API de base fonctionne")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"❌ Erreur API de base: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return
    
    # Test 2: Test JWT
    print("\n2. Test de la configuration JWT...")
    try:
        response = requests.get(f"{BASE_URL}/api/test-jwt")
        if response.status_code == 200:
            print("✅ Configuration JWT OK")
            print(f"   Réponse: {response.json()}")
        else:
            print(f"❌ Erreur JWT: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur JWT: {e}")
    
    # Test 3: Inscription d'un utilisateur de test
    print("\n3. Test d'inscription...")
    test_user = {
        "email": "test@example.com",
        "password": "test123",
        "name": "Utilisateur Test",
        "role": "user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=test_user)
        if response.status_code == 201:
            print("✅ Inscription réussie")
            print(f"   Réponse: {response.json()}")
        elif response.status_code == 400 and "déjà existant" in response.json().get("message", ""):
            print("✅ Utilisateur de test existe déjà")
        else:
            print(f"❌ Erreur inscription: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Erreur inscription: {e}")
    
    # Test 4: Connexion
    print("\n4. Test de connexion...")
    login_data = {
        "email": "test@example.com",
        "password": "test123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        if response.status_code == 200:
            print("✅ Connexion réussie")
            token = response.json().get("token")
            print(f"   Token reçu: {token[:20]}...")
            
            # Test 5: Accès aux utilisateurs (nécessite un admin)
            print("\n5. Test d'accès aux utilisateurs...")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(f"{BASE_URL}/api/users", headers=headers)
            if response.status_code == 200:
                print("✅ Accès aux utilisateurs réussi")
                users = response.json()
                print(f"   Nombre d'utilisateurs: {len(users)}")
            elif response.status_code == 403:
                print("⚠️  Accès refusé - Utilisateur non admin")
                print("   Pour tester la gestion des utilisateurs, connectez-vous avec un compte admin")
            else:
                print(f"❌ Erreur accès utilisateurs: {response.status_code}")
            
            # Test 6: Statistiques
            print("\n6. Test des statistiques...")
            response = requests.get(f"{BASE_URL}/api/users/stats", headers=headers)
            if response.status_code == 200:
                print("✅ Statistiques récupérées")
                stats = response.json()
                print(f"   Stats: {stats}")
            elif response.status_code == 403:
                print("⚠️  Statistiques refusées - Utilisateur non admin")
            else:
                print(f"❌ Erreur statistiques: {response.status_code}")
                
        else:
            print(f"❌ Erreur connexion: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Erreur connexion: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Tests terminés!")
    print("\nPour tester la gestion des utilisateurs:")
    print("1. Créez un compte admin via l'API")
    print("2. Connectez-vous avec ce compte")
    print("3. Accédez à http://localhost:8000/admin")

if __name__ == "__main__":
    test_api()

