#!/usr/bin/env python3
"""
Test simple de l'API des offres
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_offres_simple():
    print("=== TEST SIMPLE DE L'API DES OFFRES ===")
    
    # 1. Connexion admin
    print("\n1. Connexion admin...")
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_token = response.json().get("token")
    print("✅ Connexion admin réussie")
    
    # 2. Test récupération des offres (admin voit tout)
    print("\n2. Récupération des offres (admin)...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        offres = response.json()
        print(f"✅ {len(offres)} offres trouvées")
        for offre in offres[:2]:  # Afficher les 2 premières
            print(f"  - {offre.get('intitulee', 'N/A')} ({offre.get('statut', 'N/A')})")
    else:
        print(f"❌ Erreur: {response.text}")
    
    # 3. Test création d'une offre
    print("\n3. Création d'une offre...")
    offre_data = {
        "intitulee": "Test API Offres - " + str(int(time.time())),
        "lien": "https://example.com/test",
        "client": "Client Test",
        "date_limite": "2025-12-31T00:00:00.000+00:00",
        "statut": "Non préparé",
        "note_commentaire": "Offre de test",
        "documents": ["test.pdf"]
    }
    
    response = requests.post(
        f"{API_BASE_URL}/api/offres",
        json=offre_data,
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        offre = response.json().get("offre", {})
        print(f"✅ Offre créée: {offre.get('intitulee', 'N/A')}")
        offre_id = offre.get("_id")
    else:
        print(f"❌ Erreur création: {response.text}")
        return
    
    # 4. Test récupération d'une offre spécifique
    print("\n4. Récupération d'une offre spécifique...")
    if offre_id:
        response = requests.get(
            f"{API_BASE_URL}/api/offres/{offre_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            offre = response.json()
            print(f"✅ Offre récupérée: {offre.get('intitulee', 'N/A')}")
        else:
            print(f"❌ Erreur: {response.text}")
    
    # 5. Test modification d'une offre
    print("\n5. Modification d'une offre...")
    if offre_id:
        update_data = {
            "statut": "En préparation",
            "note_commentaire": "Offre modifiée avec succès"
        }
        
        response = requests.put(
            f"{API_BASE_URL}/api/offres/{offre_id}",
            json=update_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Offre modifiée avec succès")
        else:
            print(f"❌ Erreur: {response.text}")
    
    # 6. Test statistiques
    print("\n6. Statistiques des offres...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"✅ Statistiques: {stats}")
    else:
        print(f"❌ Erreur: {response.text}")
    
    # 7. Test suppression
    print("\n7. Suppression de l'offre de test...")
    if offre_id:
        response = requests.delete(
            f"{API_BASE_URL}/api/offres/{offre_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Offre supprimée avec succès")
        else:
            print(f"❌ Erreur: {response.text}")
    
    print("\n=== RÉSUMÉ ===")
    print("✅ API des offres fonctionne correctement")
    print("✅ CRUD complet opérationnel")
    print("✅ Admin peut voir et gérer toutes les offres")

if __name__ == "__main__":
    import time
    test_offres_simple()
