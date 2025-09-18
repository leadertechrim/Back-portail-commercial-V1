#!/usr/bin/env python3
"""
Test de la base de données - Collection offres
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def test_database_offres():
    print("=== TEST DE LA BASE DE DONNÉES - COLLECTION OFFRES ===")
    
    # 1. Test de connexion à la collection
    print("\n1. Test de connexion à la collection offres...")
    response = requests.get(f"{API_BASE_URL}/api/test-offres")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Connexion réussie")
        print(f"📊 Nombre total d'offres dans la collection: {data.get('count', 0)}")
    else:
        print(f"❌ Erreur de connexion: {response.status_code}")
        return
    
    # 2. Connexion admin pour récupérer les données
    print("\n2. Connexion en tant qu'admin...")
    admin_login = {
        "email": "admin@test.com",
        "password": "admin123"
    }
    
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_token = response.json().get("token")
    print("✅ Connexion admin réussie")
    
    # 3. Récupération de toutes les offres
    print("\n3. Récupération de toutes les offres...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code != 200:
        print(f"❌ Erreur lors de la récupération: {response.status_code}")
        print(f"Message: {response.text}")
        return
    
    offres = response.json()
    print(f"✅ {len(offres)} offres récupérées avec succès")
    
    # 4. Affichage détaillé des offres
    print("\n4. Détails des offres:")
    print("=" * 80)
    
    for i, offre in enumerate(offres, 1):
        print(f"\n📋 OFFRE {i}:")
        print(f"   🆔 ID: {offre.get('_id', 'N/A')}")
        print(f"   📝 Intitulé: {offre.get('intitulee', 'N/A')}")
        print(f"   🔗 Lien: {offre.get('lien', 'N/A')}")
        print(f"   👤 Client: {offre.get('client', 'N/A')}")
        print(f"   📅 Date limite: {offre.get('date_limite', 'N/A')}")
        print(f"   📊 Statut: {offre.get('statut', 'N/A')}")
        print(f"   👨‍💼 Responsable ID: {offre.get('responsable_id', 'N/A')}")
        print(f"   💬 Note/Commentaire: {offre.get('note_commentaire', 'N/A')}")
        
        documents = offre.get('documents', [])
        print(f"   📎 Documents ({len(documents)}):")
        if documents:
            for j, doc in enumerate(documents, 1):
                print(f"      {j}. {doc}")
        else:
            print("      Aucun document")
        
        print(f"   📅 Créé le: {offre.get('created_at', 'N/A')}")
        print(f"   📅 Modifié le: {offre.get('updated_at', 'N/A')}")
        print("-" * 60)
    
    # 5. Statistiques
    print("\n5. Statistiques des offres...")
    response = requests.get(
        f"{API_BASE_URL}/api/offres/stats",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    
    if response.status_code == 200:
        stats = response.json()
        print("📊 STATISTIQUES:")
        print(f"   • Total des offres: {stats.get('total_offres', 0)}")
        print(f"   • Non préparées: {stats.get('non_prepare_offres', 0)}")
        print(f"   • En préparation: {stats.get('en_preparation_offres', 0)}")
        print(f"   • Envoyées: {stats.get('envoyee_offres', 0)}")
    else:
        print(f"❌ Erreur lors de la récupération des statistiques: {response.status_code}")
    
    print("\n" + "=" * 80)
    print("✅ Test de la base de données terminé")

if __name__ == "__main__":
    test_database_offres()
