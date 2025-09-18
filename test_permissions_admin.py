#!/usr/bin/env python3
"""
Test des permissions admin
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_permissions_admin():
    print("=== TEST PERMISSIONS ADMIN ===")
    
    # Connexion admin
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_data = response.json()
    admin_token = admin_data.get("token")
    admin_id = admin_data.get("user_id")
    print(f"✅ Connexion admin réussie - ID: {admin_id}")
    
    # Lire toutes les offres
    response = requests.get(f"{API_BASE_URL}/api/offres", headers={"Authorization": f"Bearer {admin_token}"})
    if response.status_code != 200:
        print(f"❌ Erreur lecture: {response.status_code}")
        return
    
    offres = response.json()
    print(f"✅ Admin voit {len(offres)} offres")
    
    # Modifier une offre d'un autre utilisateur
    for offre in offres:
        responsable_id = offre.get("responsable_id", "")
        intitulee = offre.get("intitulee", "N/A")
        
        if str(responsable_id) != str(admin_id):  # Offre d'un autre utilisateur
            print(f"\n📋 Test modification par admin de: {intitulee}")
            print(f"   - Responsable: {responsable_id}")
            print(f"   - Admin ID: {admin_id}")
            
            # Essayer de modifier cette offre
            update_data = {"statut": "Envoyée"}
            response = requests.put(
                f"{API_BASE_URL}/api/offres/{offre.get('_id')}",
                json=update_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            print(f"   - Status modification: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Correct: Admin peut modifier cette offre")
            else:
                print("   ❌ Incorrect: Admin ne peut pas modifier cette offre")
                print(f"   - Response: {response.text}")
            break
    
    # Test réassignation par l'admin
    print(f"\n📋 Test réassignation par l'admin...")
    for offre in offres:
        responsable_id = offre.get("responsable_id", "")
        intitulee = offre.get("intitulee", "N/A")
        
        if str(responsable_id) != str(admin_id):  # Offre d'un autre utilisateur
            print(f"   - Offre: {intitulee}")
            print(f"   - Responsable actuel: {responsable_id}")
            
            # Essayer de réassigner cette offre
            update_data = {"responsable_id": admin_id}
            response = requests.put(
                f"{API_BASE_URL}/api/offres/{offre.get('_id')}",
                json=update_data,
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            print(f"   - Status réassignation: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Correct: Admin peut réassigner cette offre")
            else:
                print("   ❌ Incorrect: Admin ne peut pas réassigner cette offre")
                print(f"   - Response: {response.text}")
            break

if __name__ == "__main__":
    test_permissions_admin()
