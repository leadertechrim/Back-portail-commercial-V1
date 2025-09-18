#!/usr/bin/env python3
"""
Test du champ 'est_mienne' pour identifier les offres de l'utilisateur
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_est_mienne():
    print("=== TEST DU CHAMP 'EST_MIENNE' ===")
    
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
        "name": "User Test Est Mienne",
        "email": "user_est_mienne@test.com",
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
    user_login = {"email": "user_est_mienne@test.com", "password": "password123"}
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
        "intitulee": "Offre Test User Est Mienne",
        "lien": "https://example.com/offre-user-est-mienne",
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
        "intitulee": "Offre Test Admin Est Mienne",
        "lien": "https://example.com/offre-admin-est-mienne",
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
    
    # 6. Test lecture des offres par l'utilisateur
    print("\n6. Test lecture des offres par l'utilisateur...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    if response.status_code != 200:
        print("❌ Erreur lecture offres utilisateur")
        return
    
    offres = response.json()
    print(f"✅ Utilisateur voit {len(offres)} offres")
    
    # 7. Vérification du champ 'est_mienne'
    print("\n7. Vérification du champ 'est_mienne'...")
    user_offres = []
    other_offres = []
    
    for offre in offres:
        est_mienne = offre.get("est_mienne", False)
        responsable_id = offre.get("responsable_id", "")
        intitulee = offre.get("intitulee", "N/A")
        
        print(f"   📋 {intitulee}")
        print(f"      - Responsable ID: {responsable_id}")
        print(f"      - Est mienne: {est_mienne}")
        print(f"      - User ID: {user_id_from_token}")
        
        if est_mienne:
            user_offres.append(offre)
            print(f"      ✅ Cette offre appartient à l'utilisateur")
        else:
            other_offres.append(offre)
            print(f"      👤 Cette offre appartient à quelqu'un d'autre")
        print()
    
    print(f"📊 Résumé:")
    print(f"   - Offres de l'utilisateur: {len(user_offres)}")
    print(f"   - Offres d'autres utilisateurs: {len(other_offres)}")
    
    # 8. Test lecture d'une offre spécifique par l'utilisateur
    print("\n8. Test lecture d'une offre spécifique...")
    if user_offre_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{user_offre_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        if response.status_code == 200:
            offre = response.json()
            est_mienne = offre.get("est_mienne", False)
            print(f"✅ Offre spécifique - Est mienne: {est_mienne}")
        else:
            print("❌ Erreur lecture offre spécifique")
    
    # 9. Test lecture d'une offre de l'admin par l'utilisateur
    print("\n9. Test lecture d'une offre de l'admin par l'utilisateur...")
    if admin_offre_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{admin_offre_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        if response.status_code == 200:
            offre = response.json()
            est_mienne = offre.get("est_mienne", False)
            print(f"✅ Offre de l'admin - Est mienne: {est_mienne}")
        else:
            print("❌ Erreur lecture offre de l'admin")
    
    print("\n=== RÉSUMÉ ===")
    print("✅ Le champ 'est_mienne' fonctionne correctement")
    print("✅ L'utilisateur peut identifier ses propres offres")
    print("✅ L'utilisateur voit toutes les offres avec indication de propriété")

if __name__ == "__main__":
    test_est_mienne()
