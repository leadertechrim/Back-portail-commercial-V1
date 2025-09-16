#!/usr/bin/env python3
"""
Script de test pour l'API de gestion des utilisateurs
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_user_management():
    print("🧪 Test de l'API de gestion des utilisateurs")
    print("=" * 60)
    
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
    
    # Test 3: Inscription d'un utilisateur admin de test
    print("\n3. Test d'inscription admin...")
    admin_user = {
        "email": "admin@test.com",
        "password": "admin123",
        "name": "Admin Test",
        "role": "admin"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/register", json=admin_user)
        if response.status_code == 201:
            print("✅ Inscription admin réussie")
            print(f"   Réponse: {response.json()}")
        elif response.status_code == 400 and "déjà existant" in response.json().get("message", ""):
            print("✅ Admin de test existe déjà")
        else:
            print(f"❌ Erreur inscription admin: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Erreur inscription admin: {e}")
    
    # Test 4: Connexion admin
    print("\n4. Test de connexion admin...")
    login_data = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/login", json=login_data)
        if response.status_code == 200:
            print("✅ Connexion admin réussie")
            token = response.json().get("token")
            print(f"   Token reçu: {token[:20]}...")
            
            # Test 5: Récupérer la liste des utilisateurs
            print("\n5. Test de récupération des utilisateurs...")
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(f"{BASE_URL}/api/users", headers=headers)
            if response.status_code == 200:
                print("✅ Liste des utilisateurs récupérée")
                users = response.json()
                print(f"   Nombre d'utilisateurs: {len(users)}")
                for user in users:
                    print(f"   - {user.get('name', 'N/A')} ({user.get('email')}) - {user.get('role')}")
            else:
                print(f"❌ Erreur récupération utilisateurs: {response.status_code}")
            
            # Test 6: Statistiques des utilisateurs
            print("\n6. Test des statistiques...")
            response = requests.get(f"{BASE_URL}/api/users/stats", headers=headers)
            if response.status_code == 200:
                print("✅ Statistiques récupérées")
                stats = response.json()
                print(f"   Stats: {stats}")
            else:
                print(f"❌ Erreur statistiques: {response.status_code}")
            
            # Test 7: Créer un nouvel utilisateur
            print("\n7. Test de création d'utilisateur...")
            new_user = {
                "name": "Utilisateur Test",
                "email": "user@test.com",
                "password": "user123",
                "role": "user"
            }
            
            response = requests.post(f"{BASE_URL}/api/users", headers=headers, json=new_user)
            if response.status_code == 201:
                print("✅ Utilisateur créé avec succès")
                created_user = response.json()
                user_id = created_user["user"]["_id"]
                print(f"   ID utilisateur: {user_id}")
                
                # Test 8: Modifier l'utilisateur
                print("\n8. Test de modification d'utilisateur...")
                update_data = {
                    "name": "Utilisateur Modifié",
                    "role": "admin"
                }
                
                response = requests.put(f"{BASE_URL}/api/users/{user_id}", headers=headers, json=update_data)
                if response.status_code == 200:
                    print("✅ Utilisateur modifié avec succès")
                    print(f"   Réponse: {response.json()}")
                else:
                    print(f"❌ Erreur modification: {response.status_code} - {response.json()}")
                
                # Test 9: Changer le mot de passe
                print("\n9. Test de changement de mot de passe...")
                password_data = {
                    "newPassword": "newpassword123"
                }
                
                response = requests.post(f"{BASE_URL}/api/users/{user_id}/change-password", headers=headers, json=password_data)
                if response.status_code == 200:
                    print("✅ Mot de passe changé avec succès")
                    print(f"   Réponse: {response.json()}")
                else:
                    print(f"❌ Erreur changement mot de passe: {response.status_code} - {response.json()}")
                
                # Test 10: Supprimer l'utilisateur
                print("\n10. Test de suppression d'utilisateur...")
                response = requests.delete(f"{BASE_URL}/api/users/{user_id}", headers=headers)
                if response.status_code == 200:
                    print("✅ Utilisateur supprimé avec succès")
                    print(f"   Réponse: {response.json()}")
                else:
                    print(f"❌ Erreur suppression: {response.status_code} - {response.json()}")
                
            else:
                print(f"❌ Erreur création utilisateur: {response.status_code} - {response.json()}")
                
        else:
            print(f"❌ Erreur connexion admin: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"❌ Erreur connexion admin: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Tests terminés!")
    print("\nRésumé des routes testées:")
    print("✅ GET /api/test")
    print("✅ GET /api/test-jwt")
    print("✅ POST /register")
    print("✅ POST /login")
    print("✅ GET /api/users")
    print("✅ GET /api/users/stats")
    print("✅ POST /api/users")
    print("✅ PUT /api/users/<id>")
    print("✅ POST /api/users/<id>/change-password")
    print("✅ DELETE /api/users/<id>")

if __name__ == "__main__":
    test_user_management()
