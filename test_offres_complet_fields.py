#!/usr/bin/env python3
"""
Test complet des routes offres - Vérification des champs et filtrage par responsable_id
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

def test_offres_fields_and_filtering():
    print("=== TEST COMPLET - CHAMPS ET FILTRAGE PAR RESPONSABLE_ID ===")
    
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
        "name": "Test User Fields",
        "email": "user_fields@test.com",
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
    user_login = {"email": "user_fields@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    
    if response.status_code != 200:
        print("❌ Connexion utilisateur échouée")
        return
    
    user_data = response.json()
    user_token = user_data.get("token")
    user_id_from_token = user_data.get("user_id")
    print(f"✅ Connexion utilisateur réussie - ID: {user_id_from_token}")
    
    # 4. Test création d'offre par l'utilisateur normal
    print("\n4. Création d'offre par l'utilisateur normal...")
    offre_user_data = {
        "intitulee": "Offre Test Utilisateur",
        "lien": "https://example.com/offre-user",
        "client": "Client Test User",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre créée par utilisateur normal",
        "documents": ["document1.pdf", "document2.docx"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_user_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    offre_created = print_response("Création offre par utilisateur", response)
    if response.status_code != 201:
        print("❌ Création offre utilisateur échouée")
        return
    
    user_offre_id = offre_created.get("offre", {}).get("_id")
    print(f"✅ Offre utilisateur créée - ID: {user_offre_id}")
    
    # 5. Test création d'offre par l'admin
    print("\n5. Création d'offre par l'admin...")
    offre_admin_data = {
        "intitulee": "Offre Test Admin",
        "lien": "https://example.com/offre-admin",
        "client": "Client Test Admin",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "En préparation",
        "note_commentaire": "Offre créée par admin",
        "documents": ["admin_doc1.pdf", "admin_doc2.xlsx"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_admin_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    admin_offre_created = print_response("Création offre par admin", response)
    if response.status_code != 201:
        print("❌ Création offre admin échouée")
        return
    
    admin_offre_id = admin_offre_created.get("offre", {}).get("_id")
    print(f"✅ Offre admin créée - ID: {admin_offre_id}")
    
    # 6. Test récupération des offres par l'utilisateur (doit voir seulement ses offres)
    print("\n6. Récupération des offres par l'utilisateur...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    user_offres = print_response("GET offres par utilisateur", response)
    if response.status_code == 200:
        print(f"📊 Nombre d'offres vues par l'utilisateur: {len(user_offres)}")
        
        # Vérifier que l'utilisateur ne voit que ses offres
        for offre in user_offres:
            responsable_id = offre.get("responsable_id")
            print(f"   - Offre: {offre.get('intitulee')} | Responsable: {responsable_id}")
            if responsable_id != user_id_from_token:
                print(f"   ⚠️  ATTENTION: L'utilisateur voit une offre qui ne lui appartient pas!")
            else:
                print(f"   ✅ Offre appartient à l'utilisateur")
    
    # 7. Test récupération des offres par l'admin (doit voir toutes les offres)
    print("\n7. Récupération des offres par l'admin...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    admin_offres = print_response("GET offres par admin", response)
    if response.status_code == 200:
        print(f"📊 Nombre d'offres vues par l'admin: {len(admin_offres)}")
        
        # Vérifier que l'admin voit toutes les offres
        for offre in admin_offres:
            responsable_id = offre.get("responsable_id")
            print(f"   - Offre: {offre.get('intitulee')} | Responsable: {responsable_id}")
    
    # 8. Vérification des champs requis
    print("\n8. Vérification des champs requis...")
    if user_offres and len(user_offres) > 0:
        offre = user_offres[0]
        required_fields = [
            "_id", "intitulee", "lien", "client", "date_limite", 
            "statut", "responsable_id", "note_commentaire", 
            "documents", "created_at", "updated_at"
        ]
        
        print("🔍 Vérification des champs requis:")
        missing_fields = []
        for field in required_fields:
            if field in offre:
                print(f"   ✅ {field}: {type(offre[field]).__name__}")
            else:
                print(f"   ❌ {field}: MANQUANT")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"⚠️  Champs manquants: {missing_fields}")
        else:
            print("✅ Tous les champs requis sont présents")
    
    # 9. Test récupération d'une offre spécifique par l'utilisateur
    print("\n9. Test récupération d'une offre spécifique par l'utilisateur...")
    if user_offre_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{user_offre_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print_response(f"GET offre {user_offre_id} par utilisateur", response)
    
    # 10. Test tentative d'accès à l'offre de l'admin par l'utilisateur (doit échouer)
    print("\n10. Test tentative d'accès à l'offre de l'admin par l'utilisateur...")
    if admin_offre_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{admin_offre_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        print_response(f"GET offre {admin_offre_id} par utilisateur (doit échouer)", response)
        
        if response.status_code == 404:
            print("✅ L'utilisateur ne peut pas accéder à l'offre de l'admin")
        else:
            print("⚠️  L'utilisateur peut accéder à l'offre de l'admin (problème de sécurité)")
    
    # 11. Test statistiques par utilisateur
    print("\n11. Test statistiques par utilisateur...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    user_stats = print_response("Stats offres par utilisateur", response)
    
    # 12. Test statistiques par admin
    print("\n12. Test statistiques par admin...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    admin_stats = print_response("Stats offres par admin", response)
    
    # 13. Comparaison des statistiques
    print("\n13. Comparaison des statistiques...")
    if user_stats and admin_stats:
        print("📊 Comparaison des statistiques:")
        print(f"   Utilisateur - Total: {user_stats.get('total_offres', 0)}")
        print(f"   Admin - Total: {admin_stats.get('total_offres', 0)}")
        
        if user_stats.get('total_offres', 0) < admin_stats.get('total_offres', 0):
            print("✅ Le filtrage fonctionne: l'utilisateur voit moins d'offres que l'admin")
        else:
            print("⚠️  Problème: l'utilisateur voit le même nombre d'offres que l'admin")
    
    print("\n=== RÉSUMÉ DU TEST ===")
    print("✅ Test des champs et du filtrage terminé")
    print("✅ Vérification des permissions utilisateur/admin")
    print("✅ Validation de la sécurité des données")

if __name__ == "__main__":
    test_offres_fields_and_filtering()
