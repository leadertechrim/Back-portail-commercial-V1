#!/usr/bin/env python3
"""
Test simple des nouvelles permissions
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_permissions_simple():
    print("=== TEST SIMPLE DES NOUVELLES PERMISSIONS ===")
    
    # 1. Connexion admin
    print("\n1. Connexion admin...")
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_token = response.json().get("token")
    print("✅ Connexion admin réussie")
    
    # 2. Test lecture des offres - Admin (doit voir toutes les offres)
    print("\n2. Test lecture des offres - Admin...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        offres = response.json()
        print(f"✅ Admin voit {len(offres)} offres")
        
        if len(offres) > 0:
            print("📋 Première offre:")
            offre = offres[0]
            print(f"   - Intitulé: {offre.get('intitulee', 'N/A')}")
            print(f"   - Client: {offre.get('client', 'N/A')}")
            print(f"   - Responsable: {offre.get('responsable_id', 'N/A')}")
    else:
        print(f"❌ Erreur lecture offres admin: {response.status_code}")
    
    # 3. Test création d'offre - Admin
    print("\n3. Test création d'offre - Admin...")
    offre_data = {
        "intitulee": "Test Permissions Admin",
        "lien": "https://example.com/test-admin",
        "client": "Client Test Admin",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Test permissions admin",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        print("✅ Admin peut créer des offres")
        admin_offre_id = response.json().get("offre", {}).get("_id")
    else:
        print(f"❌ Admin ne peut pas créer d'offres: {response.text}")
        admin_offre_id = None
    
    # 4. Test modification d'offre - Admin
    print("\n4. Test modification d'offre - Admin...")
    if admin_offre_id:
        update_data = {
            "statut": "En préparation",
            "note_commentaire": "Modifiée par admin"
        }
        
        response = requests.put(
            f"{API_BASE_URL}/api/offres/{admin_offre_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Admin peut modifier des offres")
        else:
            print(f"❌ Admin ne peut pas modifier d'offres: {response.text}")
    
    # 5. Test suppression d'offre - Admin
    print("\n5. Test suppression d'offre - Admin...")
    if admin_offre_id:
        response = requests.delete(
            f"{API_BASE_URL}/api/offres/{admin_offre_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Admin peut supprimer des offres")
        else:
            print(f"❌ Admin ne peut pas supprimer d'offres: {response.text}")
    
    # 6. Test statistiques - Admin
    print("\n6. Test statistiques - Admin...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Statistiques admin: {stats}")
    else:
        print(f"❌ Erreur statistiques admin: {response.text}")
    
    print("\n=== RÉSUMÉ ===")
    print("✅ Test des permissions terminé")

if __name__ == "__main__":
    test_permissions_simple()
