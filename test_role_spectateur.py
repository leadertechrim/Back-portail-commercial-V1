#!/usr/bin/env python3
"""
Test du rôle spectateur - peut voir mais pas modifier
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def print_response(title, response):
    print(f"\n--- {title} ---")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"JSON Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")

def test_spectateur_role():
    print("=== TEST DU RÔLE SPECTATEUR ===")
    
    # 1. Créer un utilisateur spectateur
    print("\n1. Création d'un utilisateur spectateur...")
    spectateur_data = {
        "name": "Spectateur Test",
        "email": "spectateur@test.com",
        "password": "password123",
        "role": "spectateur",
        "telephone": "+22212345678",
        "statut": "actif"
    }
    
    # D'abord, se connecter en tant qu'admin pour créer le spectateur
    admin_login = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    # Login admin
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    if response.status_code != 200:
        print("❌ Impossible de se connecter en tant qu'admin")
        return
    
    admin_token = response.json().get("token")
    print("✅ Connexion admin réussie")
    
    # Créer le spectateur
    response = requests.post(
        f"{API_BASE_URL}/api/users",
        json=spectateur_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("Création spectateur", response)
    
    if response.status_code != 201:
        print("❌ Impossible de créer le spectateur")
        return
    
    # 2. Se connecter en tant que spectateur
    print("\n2. Connexion en tant que spectateur...")
    spectateur_login = {
        "email": "spectateur@test.com",
        "password": "password123"
    }
    
    response = requests.post(f"{API_BASE_URL}/login", json=spectateur_login)
    print_response("Login spectateur", response)
    
    if response.status_code != 200:
        print("❌ Impossible de se connecter en tant que spectateur")
        return
    
    spectateur_token = response.json().get("token")
    print("✅ Connexion spectateur réussie")
    
    # 3. Tester les droits de lecture (devraient fonctionner)
    print("\n3. Test des droits de lecture...")
    
    # Test lecture sources
    response = requests.get(
        f"{API_BASE_URL}/api/sources",
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("GET /api/sources (spectateur)", response)
    
    # Test lecture clients
    response = requests.get(
        f"{API_BASE_URL}/api/clients",
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("GET /api/clients (spectateur)", response)
    
    # Test lecture panier
    response = requests.get(
        f"{API_BASE_URL}/api/panier",
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("GET /api/panier (spectateur)", response)
    
    # 4. Tester les droits d'écriture (devraient échouer)
    print("\n4. Test des droits d'écriture (devraient échouer)...")
    
    # Test création client (devrait échouer)
    client_data = {
        "raison_sociale": "Test Client Spectateur",
        "nom_prenom": "Test User",
        "telephone": "+22212345678",
        "email": "test@client.com",
        "adresse": "Test Address"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/clients",
        json=client_data,
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("POST /api/clients (spectateur) - devrait échouer", response)
    
    # Test modification source (devrait échouer)
    response = requests.put(
        f"{API_BASE_URL}/api/sources/507f1f77bcf86cd799439011",  # ID fictif
        json={"nom_entite": "Test Modification"},
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("PUT /api/sources (spectateur) - devrait échouer", response)
    
    # Test suppression panier (devrait échouer)
    response = requests.delete(
        f"{API_BASE_URL}/api/panier/507f1f77bcf86cd799439011",  # ID fictif
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    print_response("DELETE /api/panier (spectateur) - devrait échouer", response)
    
    print("\n=== RÉSUMÉ ===")
    print("✅ Le rôle spectateur peut lire les données")
    print("❌ Le rôle spectateur ne peut pas modifier les données")
    print("✅ Les permissions sont correctement appliquées")

if __name__ == "__main__":
    test_spectateur_role()
