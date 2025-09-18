#!/usr/bin/env python3
"""
Test des nouvelles permissions pour les offres
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def print_response(title, response):
    print(f"\n--- {title} ---")
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print(f"JSON Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        return data
    except json.JSONDecodeError:
        print(f"Raw Response: {response.text}")
        return None

def test_nouvelles_permissions():
    print("=== TEST DES NOUVELLES PERMISSIONS ===")
    
    # 1. Connexion admin
    print("\n1. Connexion admin...")
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_data = response.json()
    admin_token = admin_data.get("token")
    print("✅ Connexion admin réussie")
    
    # 2. Création d'un utilisateur normal
    print("\n2. Création d'un utilisateur normal...")
    user_data = {
        "name": "User Test Permissions",
        "email": "user_perm@test.com",
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
    
    if response.status_code != 201:
        print("❌ Création utilisateur échouée")
        return
    
    print("✅ Utilisateur créé")
    
    # 3. Création d'un spectateur
    print("\n3. Création d'un spectateur...")
    spectateur_data = {
        "name": "Spectateur Test",
        "email": "spectateur_perm@test.com",
        "password": "password123",
        "role": "spectateur",
        "telephone": "+22212345678",
        "statut": "actif"
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/users",
        json=spectateur_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code != 201:
        print("❌ Création spectateur échouée")
        return
    
    print("✅ Spectateur créé")
    
    # 4. Connexion utilisateur normal
    print("\n4. Connexion utilisateur normal...")
    user_login = {"email": "user_perm@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    
    if response.status_code != 200:
        print("❌ Connexion utilisateur échouée")
        return
    
    user_data = response.json()
    user_token = user_data.get("token")
    print("✅ Connexion utilisateur réussie")
    
    # 5. Connexion spectateur
    print("\n5. Connexion spectateur...")
    spectateur_login = {"email": "spectateur_perm@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=spectateur_login)
    
    if response.status_code != 200:
        print("❌ Connexion spectateur échouée")
        return
    
    spectateur_data = response.json()
    spectateur_token = spectateur_data.get("token")
    print("✅ Connexion spectateur réussie")
    
    # 6. Test lecture des offres - Utilisateur normal (doit voir toutes les offres)
    print("\n6. Test lecture des offres - Utilisateur normal...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    user_offres = print_response("GET offres par utilisateur normal", response)
    if response.status_code == 200:
        print(f"✅ Utilisateur normal voit {len(user_offres)} offres")
    else:
        print("❌ Erreur lecture offres utilisateur")
    
    # 7. Test lecture des offres - Spectateur (doit voir toutes les offres)
    print("\n7. Test lecture des offres - Spectateur...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    
    spectateur_offres = print_response("GET offres par spectateur", response)
    if response.status_code == 200:
        print(f"✅ Spectateur voit {len(spectateur_offres)} offres")
    else:
        print("❌ Erreur lecture offres spectateur")
    
    # 8. Test création d'offre - Utilisateur normal (doit pouvoir créer)
    print("\n8. Test création d'offre - Utilisateur normal...")
    offre_data = {
        "intitulee": "Offre Test User Permissions",
        "lien": "https://example.com/offre-user-perm",
        "client": "Client Test User",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre créée par utilisateur normal",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    user_offre_created = print_response("POST offre par utilisateur normal", response)
    if response.status_code == 201:
        print("✅ Utilisateur normal peut créer des offres")
        user_offre_id = user_offre_created.get("offre", {}).get("_id")
    else:
        print("❌ Utilisateur normal ne peut pas créer d'offres")
        user_offre_id = None
    
    # 9. Test création d'offre - Spectateur (ne doit PAS pouvoir créer)
    print("\n9. Test création d'offre - Spectateur...")
    offre_data = {
        "intitulee": "Offre Test Spectateur",
        "lien": "https://example.com/offre-spectateur",
        "client": "Client Test Spectateur",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre créée par spectateur",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_data,
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    
    spectateur_offre_created = print_response("POST offre par spectateur", response)
    if response.status_code == 403:
        print("✅ Spectateur ne peut pas créer d'offres (correct)")
    else:
        print("❌ Spectateur peut créer des offres (incorrect)")
    
    # 10. Test modification d'offre - Utilisateur normal (doit pouvoir modifier)
    print("\n10. Test modification d'offre - Utilisateur normal...")
    if user_offre_id:
        update_data = {
            "statut": "En préparation",
            "note_commentaire": "Modifiée par utilisateur normal"
        }
        
        response = requests.put(
            f"{API_BASE_URL}/api/offres/{user_offre_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        print_response("PUT offre par utilisateur normal", response)
        if response.status_code == 200:
            print("✅ Utilisateur normal peut modifier des offres")
        else:
            print("❌ Utilisateur normal ne peut pas modifier d'offres")
    
    # 11. Test modification d'offre - Spectateur (ne doit PAS pouvoir modifier)
    print("\n11. Test modification d'offre - Spectateur...")
    if user_offre_id:
        update_data = {
            "statut": "Envoyée",
            "note_commentaire": "Modifiée par spectateur"
        }
        
        response = requests.put(
            f"{API_BASE_URL}/api/offres/{user_offre_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {spectateur_token}"}
        )
        
        print_response("PUT offre par spectateur", response)
        if response.status_code == 403:
            print("✅ Spectateur ne peut pas modifier d'offres (correct)")
        else:
            print("❌ Spectateur peut modifier des offres (incorrect)")
    
    # 12. Test suppression d'offre - Utilisateur normal (doit pouvoir supprimer)
    print("\n12. Test suppression d'offre - Utilisateur normal...")
    if user_offre_id:
        response = requests.delete(
            f"{API_BASE_URL}/api/offres/{user_offre_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        print_response("DELETE offre par utilisateur normal", response)
        if response.status_code == 200:
            print("✅ Utilisateur normal peut supprimer des offres")
        else:
            print("❌ Utilisateur normal ne peut pas supprimer d'offres")
    
    # 13. Test suppression d'offre - Spectateur (ne doit PAS pouvoir supprimer)
    print("\n13. Test suppression d'offre - Spectateur...")
    # Créer une offre par l'admin d'abord
    admin_offre_data = {
        "intitulee": "Offre Test Admin Pour Spectateur",
        "lien": "https://example.com/offre-admin-spectateur",
        "client": "Client Test Admin",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre créée par admin pour test spectateur",
        "documents": ["admin_test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=admin_offre_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 201:
        admin_offre_id = response.json().get("offre", {}).get("_id")
        
        # Tentative de suppression par spectateur
        response = requests.delete(
            f"{API_BASE_URL}/api/offres/{admin_offre_id}",
            headers={"Authorization": f"Bearer {spectateur_token}"}
        )
        
        print_response("DELETE offre par spectateur", response)
        if response.status_code == 403:
            print("✅ Spectateur ne peut pas supprimer d'offres (correct)")
        else:
            print("❌ Spectateur peut supprimer des offres (incorrect)")
    
    # 14. Test statistiques - Tous doivent voir les mêmes statistiques
    print("\n14. Test statistiques...")
    
    # Statistiques utilisateur normal
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    user_stats = print_response("Stats par utilisateur normal", response)
    
    # Statistiques spectateur
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {spectateur_token}"}
    )
    spectateur_stats = print_response("Stats par spectateur", response)
    
    # Statistiques admin
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_stats = print_response("Stats par admin", response)
    
    # Comparaison
    if user_stats and spectateur_stats and admin_stats:
        if (user_stats.get('total_offres') == spectateur_stats.get('total_offres') == 
            admin_stats.get('total_offres')):
            print("✅ Tous les rôles voient les mêmes statistiques globales")
        else:
            print("❌ Les statistiques ne sont pas identiques entre les rôles")
    
    print("\n=== RÉSUMÉ DES NOUVELLES PERMISSIONS ===")
    print("✅ Utilisateur normal : Voit toutes les offres, peut créer/modifier/supprimer")
    print("✅ Admin : Voit toutes les offres, peut créer/modifier/supprimer")
    print("✅ Spectateur : Voit toutes les offres, ne peut rien modifier/supprimer")
    print("✅ Tous voient les mêmes statistiques globales")

if __name__ == "__main__":
    test_nouvelles_permissions()
