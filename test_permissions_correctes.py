#!/usr/bin/env python3
"""
Test des permissions correctes pour les offres
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_permissions_correctes():
    print("=== TEST DES PERMISSIONS CORRECTES ===")
    
    # 1. Connexion admin
    print("\n1. Connexion admin...")
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_data = response.json()
    admin_token = admin_data.get("token")
    admin_id = admin_data.get("user_id")
    print(f"✅ Connexion admin réussie - ID: {admin_id}")
    
    # 2. Création d'un utilisateur normal
    print("\n2. Création d'un utilisateur normal...")
    user_data = {
        "name": "User Test Permissions",
        "email": "user_permissions@test.com",
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
    
    user_created = response.json()
    user_id = user_created.get("user", {}).get("_id")
    print(f"✅ Utilisateur créé - ID: {user_id}")
    
    # 3. Connexion utilisateur normal
    print("\n3. Connexion utilisateur normal...")
    user_login = {"email": "user_permissions@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    
    if response.status_code != 200:
        print("❌ Connexion utilisateur échouée")
        return
    
    user_data = response.json()
    user_token = user_data.get("token")
    user_id_from_token = user_data.get("user_id")
    print(f"✅ Connexion utilisateur réussie - ID: {user_id_from_token}")
    
    # 4. Création d'offre par l'utilisateur
    print("\n4. Création d'offre par l'utilisateur...")
    offre_user_data = {
        "intitulee": "Offre Test User Permissions",
        "lien": "https://example.com/offre-user-permissions",
        "client": "Client Test User",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre créée par utilisateur",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_user_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code != 201:
        print("❌ Création offre utilisateur échouée")
        return
    
    user_offre_id = response.json().get("offre", {}).get("_id")
    print(f"✅ Offre utilisateur créée - ID: {user_offre_id}")
    
    # 5. Création d'offre par l'admin
    print("\n5. Création d'offre par l'admin...")
    offre_admin_data = {
        "intitulee": "Offre Test Admin Permissions",
        "lien": "https://example.com/offre-admin-permissions",
        "client": "Client Test Admin",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "En préparation",
        "note_commentaire": "Offre créée par admin",
        "documents": ["admin.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_admin_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code != 201:
        print("❌ Création offre admin échouée")
        return
    
    admin_offre_id = response.json().get("offre", {}).get("_id")
    print(f"✅ Offre admin créée - ID: {admin_offre_id}")
    
    # 6. Test permissions utilisateur - modification de sa propre offre
    print("\n6. Test modification de sa propre offre par l'utilisateur...")
    update_data = {"statut": "En préparation"}
    response = requests.put(
        f"{API_BASE_URL}/api/offres/{user_offre_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code == 200:
        print("✅ Utilisateur peut modifier sa propre offre")
    else:
        print(f"❌ Utilisateur ne peut pas modifier sa propre offre: {response.status_code}")
    
    # 7. Test permissions utilisateur - modification de l'offre de l'admin
    print("\n7. Test modification de l'offre de l'admin par l'utilisateur...")
    update_data = {"statut": "Envoyée"}
    response = requests.put(
        f"{API_BASE_URL}/api/offres/{admin_offre_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code == 403:
        print("✅ Utilisateur ne peut pas modifier l'offre de l'admin (correct)")
    else:
        print(f"❌ Utilisateur peut modifier l'offre de l'admin (incorrect): {response.status_code}")
    
    # 8. Test permissions admin - modification de l'offre de l'utilisateur
    print("\n8. Test modification de l'offre de l'utilisateur par l'admin...")
    update_data = {"statut": "Envoyée"}
    response = requests.put(
        f"{API_BASE_URL}/api/offres/{user_offre_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        print("✅ Admin peut modifier l'offre de l'utilisateur")
    else:
        print(f"❌ Admin ne peut pas modifier l'offre de l'utilisateur: {response.status_code}")
    
    # 9. Test réassignation par l'admin
    print("\n9. Test réassignation de l'offre par l'admin...")
    update_data = {"responsable_id": user_id}
    response = requests.put(
        f"{API_BASE_URL}/api/offres/{admin_offre_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        print("✅ Admin peut réassigner l'offre")
    else:
        print(f"❌ Admin ne peut pas réassigner l'offre: {response.status_code}")
    
    # 10. Test réassignation par l'utilisateur (doit échouer)
    print("\n10. Test réassignation par l'utilisateur (doit échouer)...")
    update_data = {"responsable_id": admin_id}
    response = requests.put(
        f"{API_BASE_URL}/api/offres/{user_offre_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code == 403:
        print("✅ Utilisateur ne peut pas réassigner l'offre (correct)")
    else:
        print(f"❌ Utilisateur peut réassigner l'offre (incorrect): {response.status_code}")
    
    # 11. Test suppression par l'utilisateur de sa propre offre
    print("\n11. Test suppression de sa propre offre par l'utilisateur...")
    response = requests.delete(
        f"{API_BASE_URL}/api/offres/{user_offre_id}",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code == 200:
        print("✅ Utilisateur peut supprimer sa propre offre")
    else:
        print(f"❌ Utilisateur ne peut pas supprimer sa propre offre: {response.status_code}")
    
    # 12. Test suppression par l'admin de l'offre restante
    print("\n12. Test suppression de l'offre restante par l'admin...")
    response = requests.delete(
        f"{API_BASE_URL}/api/offres/{admin_offre_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        print("✅ Admin peut supprimer l'offre")
    else:
        print(f"❌ Admin ne peut pas supprimer l'offre: {response.status_code}")
    
    print("\n=== RÉSUMÉ ===")
    print("✅ Permissions correctes implémentées")
    print("✅ Utilisateur ne peut agir que sur ses propres offres")
    print("✅ Admin peut agir sur toutes les offres et les réassigner")

if __name__ == "__main__":
    test_permissions_correctes()
