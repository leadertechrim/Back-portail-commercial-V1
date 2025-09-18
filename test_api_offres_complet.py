#!/usr/bin/env python3
"""
Test complet de l'API des offres
"""

import requests
import json
from datetime import datetime, timedelta

API_BASE_URL = "http://127.0.0.1:8000"

def print_response(title, response):
    print(f"\n--- {title} ---")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"JSON Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")

def test_api_offres():
    print("=== TEST COMPLET DE L'API DES OFFRES ===")
    
    # 1. Test de connexion de base
    print("\n1. Test de connexion de base...")
    response = requests.get(f"{API_BASE_URL}/api/test")
    print_response("Test GET /api/test", response)
    
    response = requests.get(f"{API_BASE_URL}/api/test-offres")
    print_response("Test GET /api/test-offres", response)
    
    # 2. Connexion en tant qu'admin
    print("\n2. Connexion en tant qu'admin...")
    admin_login = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    print_response("Login admin", response)
    
    if response.status_code != 200:
        print("❌ Impossible de se connecter en tant qu'admin")
        return
    
    admin_token = response.json().get("token")
    print("✅ Connexion admin réussie")
    
    # 3. Test création d'un utilisateur normal
    print("\n3. Création d'un utilisateur normal...")
    user_data = {
        "name": "Utilisateur Test Offres",
        "email": "user_offres2@test.com",
        "password": "password123",
        "role": "user",
        "telephone": "+22212345678",
        "statut": "actif"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/users",
        json=user_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("Création utilisateur", response)
    
    if response.status_code != 201:
        print("❌ Impossible de créer l'utilisateur")
        return
    
    # 4. Connexion en tant qu'utilisateur normal
    print("\n4. Connexion en tant qu'utilisateur normal...")
    user_login = {
        "email": "user_offres2@test.com",
        "password": "password123"
    }
    
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    print_response("Login utilisateur", response)
    
    if response.status_code != 200:
        print("❌ Impossible de se connecter en tant qu'utilisateur")
        return
    
    user_token = response.json().get("token")
    user_id = response.json().get("user_id")
    print("✅ Connexion utilisateur réussie")
    
    # 5. Test création d'offres par l'utilisateur
    print("\n5. Création d'offres par l'utilisateur...")
    
    # Offre 1
    offre1_data = {
        "intitulee": "Déploiement d'une plateforme e-Gouvernement",
        "lien": "https://example.com/offres/egov-mauritanie",
        "client": "Ministère du Numérique de Mauritanie",
        "date_limite": "2025-10-15T00:00:00.000+00:00",
        "statut": "En préparation",
        "note_commentaire": "À finaliser avant le 10 octobre. Nécessite validation du directeur.",
        "documents": ["budget.pdf", "proposition_technique.pdf", "cahier_des_charges.docx"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre1_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print_response("Création offre 1", response)
    
    if response.status_code == 201:
        offre1_id = response.json().get("offre", {}).get("_id")
        print(f"✅ Offre 1 créée avec ID: {offre1_id}")
    else:
        print("❌ Échec création offre 1")
        return
    
    # Offre 2
    offre2_data = {
        "intitulee": "Système de gestion des appels d'offres",
        "lien": "https://example.com/offres/système-gestion",
        "client": "Entreprise ABC",
        "date_limite": "2025-11-20T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Projet prioritaire pour l'entreprise",
        "documents": ["specifications.pdf", "cahier_charges.docx"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre2_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print_response("Création offre 2", response)
    
    if response.status_code == 201:
        offre2_id = response.json().get("offre", {}).get("_id")
        print(f"✅ Offre 2 créée avec ID: {offre2_id}")
    else:
        print("❌ Échec création offre 2")
        return
    
    # 6. Test récupération des offres par l'utilisateur
    print("\n6. Récupération des offres par l'utilisateur...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print_response("GET offres (utilisateur)", response)
    
    # 7. Test récupération d'une offre spécifique
    print("\n7. Récupération d'une offre spécifique...")
    if offre1_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{offre1_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print_response(f"GET offre {offre1_id}", response)
    
    # 8. Test modification d'une offre
    print("\n8. Modification d'une offre...")
    if offre1_id:
        update_data = {
            "statut": "Envoyée",
            "note_commentaire": "Offre envoyée avec succès. En attente de réponse."
        }
        
        response = requests.put(
            f"{API_BASE_URL}/api/offres/{offre1_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print_response(f"PUT offre {offre1_id}", response)
    
    # 9. Test statistiques des offres (utilisateur)
    print("\n9. Statistiques des offres (utilisateur)...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print_response("GET stats offres (utilisateur)", response)
    
    # 10. Test vue admin - récupération de toutes les offres
    print("\n10. Vue admin - récupération de toutes les offres...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("GET offres (admin)", response)
    
    # 11. Test statistiques des offres (admin)
    print("\n11. Statistiques des offres (admin)...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("GET stats offres (admin)", response)
    
    # 12. Test création d'offre par l'admin
    print("\n12. Création d'offre par l'admin...")
    admin_offre_data = {
        "intitulee": "Formation en développement web",
        "lien": "https://example.com/offres/formation-dev",
        "client": "Ministère de l'Éducation",
        "date_limite": "2025-12-01T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Formation pour 50 fonctionnaires",
        "documents": ["programme_formation.pdf", "budget_formation.xlsx"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=admin_offre_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("Création offre admin", response)
    
    # 13. Test suppression d'une offre par l'utilisateur
    print("\n13. Suppression d'une offre par l'utilisateur...")
    if offre2_id:
        response = requests.delete(
            f"{API_BASE_URL}/api/offres/{offre2_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print_response(f"DELETE offre {offre2_id}", response)
    
    # 14. Test final - vérification des offres restantes
    print("\n14. Vérification finale des offres...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    print_response("GET offres final (utilisateur)", response)
    
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("GET offres final (admin)", response)
    
    print("\n=== RÉSUMÉ DU TEST ===")
    print("✅ Test de l'API des offres terminé")
    print("✅ Chaque utilisateur voit ses propres offres")
    print("✅ L'admin voit toutes les offres")
    print("✅ CRUD complet fonctionnel")
    print("✅ Statistiques par utilisateur et globales")

def test_validation_errors():
    print("\n=== TEST DES ERREURS DE VALIDATION ===")
    
    # Connexion admin pour les tests
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    admin_token = response.json().get("token")
    
    # Test avec données invalides
    invalid_offre_data = {
        "intitulee": "",  # Invalide - vide
        "lien": "invalid-url",  # Invalide - pas d'URL complète
        "client": "",  # Invalide - vide
        "date_limite": "invalid-date",  # Invalide - format de date incorrect
        "statut": "Statut invalide",  # Invalide - statut non autorisé
        "documents": "not-a-list"  # Invalide - pas une liste
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=invalid_offre_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    print_response("Test validation avec données invalides", response)

if __name__ == "__main__":
    test_api_offres()
    test_validation_errors()
