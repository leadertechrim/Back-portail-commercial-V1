#!/usr/bin/env python3
"""
Test des permissions utilisateur normal
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_permissions_user():
    print("=== TEST PERMISSIONS UTILISATEUR NORMAL ===")
    
    # Connexion utilisateur existant
    user_login = {"email": "user_offres2@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    
    if response.status_code != 200:
        print("❌ Connexion échouée")
        return
    
    user_data = response.json()
    user_token = user_data.get("token")
    user_id = user_data.get("user_id")
    print(f"✅ Connexion utilisateur réussie - ID: {user_id}")
    
    # Lire toutes les offres
    response = requests.get(f"{API_BASE_URL}/api/offres", headers={"Authorization": f"Bearer {user_token}"})
    if response.status_code != 200:
        print(f"❌ Erreur lecture: {response.status_code}")
        return
    
    offres = response.json()
    print(f"✅ Utilisateur voit {len(offres)} offres")
    
    # Trouver une offre qui n'appartient pas à l'utilisateur
    for offre in offres:
        est_mienne = offre.get("est_mienne", False)
        responsable_id = offre.get("responsable_id", "")
        intitulee = offre.get("intitulee", "N/A")
        
        if not est_mienne:  # Offre qui n'appartient pas à l'utilisateur
            print(f"\n📋 Test modification de: {intitulee}")
            print(f"   - Responsable: {responsable_id}")
            print(f"   - User ID: {user_id}")
            print(f"   - Est mienne: {est_mienne}")
            
            # Essayer de modifier cette offre
            update_data = {"statut": "Test Modification"}
            response = requests.put(
                f"{API_BASE_URL}/api/offres/{offre.get('_id')}",
                json=update_data,
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            print(f"   - Status modification: {response.status_code}")
            if response.status_code == 403:
                print("   ✅ Correct: Utilisateur ne peut pas modifier cette offre")
            else:
                print("   ❌ Incorrect: Utilisateur peut modifier cette offre")
                print(f"   - Response: {response.text}")
            break
    
    # Trouver une offre qui appartient à l'utilisateur
    for offre in offres:
        est_mienne = offre.get("est_mienne", False)
        responsable_id = offre.get("responsable_id", "")
        intitulee = offre.get("intitulee", "N/A")
        
        if est_mienne:  # Offre qui appartient à l'utilisateur
            print(f"\n📋 Test modification de sa propre offre: {intitulee}")
            print(f"   - Responsable: {responsable_id}")
            print(f"   - User ID: {user_id}")
            print(f"   - Est mienne: {est_mienne}")
            
            # Essayer de modifier cette offre
            update_data = {"statut": "En préparation"}
            response = requests.put(
                f"{API_BASE_URL}/api/offres/{offre.get('_id')}",
                json=update_data,
                headers={"Authorization": f"Bearer {user_token}"}
            )
            
            print(f"   - Status modification: {response.status_code}")
            if response.status_code == 200:
                print("   ✅ Correct: Utilisateur peut modifier sa propre offre")
            else:
                print("   ❌ Incorrect: Utilisateur ne peut pas modifier sa propre offre")
                print(f"   - Response: {response.text}")
            break

if __name__ == "__main__":
    test_permissions_user()
