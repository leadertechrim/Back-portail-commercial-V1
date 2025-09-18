#!/usr/bin/env python3
"""
Test simple du champ est_mienne
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_est_mienne_simple():
    print("=== TEST SIMPLE DU CHAMP EST_MIENNE ===")
    
    # Connexion utilisateur
    user_login = {"email": "user_offres2@test.com", "password": "password123"}
    response = requests.post(f"{API_BASE_URL}/login", json=user_login)
    
    if response.status_code != 200:
        print("❌ Connexion échouée")
        return
    
    user_data = response.json()
    user_token = user_data.get("token")
    user_id = user_data.get("user_id")
    print(f"✅ Connexion utilisateur réussie - ID: {user_id}")
    
    # Créer une offre
    offre_data = {
        "intitulee": "Test Est Mienne Final",
        "lien": "https://example.com/test-final",
        "client": "Client Test Final",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Test final est_mienne",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_data,
        headers={"Authorization": f"Bearer {user_token}"}
    )
    
    print(f"Création offre: {response.status_code}")
    
    if response.status_code == 201:
        offre_created = response.json()
        offre_id = offre_created.get("offre", {}).get("_id")
        responsable_id = offre_created.get("offre", {}).get("responsable_id")
        print(f"✅ Offre créée - ID: {offre_id}")
        print(f"Responsable ID dans l'offre: {responsable_id}")
        print(f"User ID connecté: {user_id}")
        print(f"Match: {str(responsable_id) == str(user_id)}")
        
        # Maintenant lire toutes les offres
        response = requests.get(
            f"{API_BASE_URL}/api/offres",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        
        if response.status_code == 200:
            offres = response.json()
            print(f"\n📋 Vérification des offres:")
            
            for offre in offres:
                if "Test Est Mienne Final" in offre.get("intitulee", ""):
                    est_mienne = offre.get("est_mienne", False)
                    responsable_id = offre.get("responsable_id", "")
                    print(f"   - Intitulé: {offre.get('intitulee')}")
                    print(f"   - Responsable: {responsable_id}")
                    print(f"   - Est mienne: {est_mienne}")
                    print(f"   - User ID: {user_id}")
                    print(f"   - Match: {str(responsable_id) == str(user_id)}")
                    break
        else:
            print(f"❌ Erreur lecture: {response.status_code}")
    else:
        print(f"❌ Erreur création: {response.text}")

if __name__ == "__main__":
    test_est_mienne_simple()
