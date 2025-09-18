#!/usr/bin/env python3
"""
Vérification des offres pour un utilisateur spécifique
"""

import requests
import json

API_BASE_URL = "http://127.0.0.1:8000"

def verifier_offres_utilisateur():
    print("=== VÉRIFICATION DES OFFRES POUR L'UTILISATEUR 68c05faf640888e4d0018d77 ===")
    
    # Connexion admin pour voir toutes les offres
    admin_login = {"email": "admin@test.com", "password": "admin123"}
    response = requests.post(f"{API_BASE_URL}/login", json=admin_login)
    
    if response.status_code != 200:
        print("❌ Connexion admin échouée")
        return
    
    admin_data = response.json()
    admin_token = admin_data.get("token")
    print("✅ Connexion admin réussie")
    
    # Lire toutes les offres
    response = requests.get(f"{API_BASE_URL}/api/offres", headers={"Authorization": f"Bearer {admin_token}"})
    if response.status_code != 200:
        print(f"❌ Erreur lecture: {response.status_code}")
        return
    
    offres = response.json()
    print(f"✅ Total des offres: {len(offres)}")
    
    # Chercher les offres de cet utilisateur
    user_id = "68c05faf640888e4d0018d77"
    user_offres = []
    
    for offre in offres:
        responsable_id = offre.get("responsable_id", "")
        if str(responsable_id) == str(user_id):
            user_offres.append(offre)
    
    print(f"\n📋 Offres de l'utilisateur {user_id}:")
    if user_offres:
        for offre in user_offres:
            print(f"   - ID: {offre.get('_id')}")
            print(f"   - Intitulé: {offre.get('intitulee')}")
            print(f"   - Client: {offre.get('client')}")
            print(f"   - Statut: {offre.get('statut')}")
            print(f"   - Responsable ID: {offre.get('responsable_id')}")
            print(f"   - Créée le: {offre.get('created_at')}")
            print()
    else:
        print("   ❌ Aucune offre trouvée pour cet utilisateur")
    
    # Afficher toutes les offres avec leurs responsables
    print("\n📋 Toutes les offres avec leurs responsables:")
    for offre in offres:
        print(f"   - {offre.get('intitulee')} (Responsable: {offre.get('responsable_id')})")
    
    # Vérifier si l'utilisateur existe
    print(f"\n🔍 Vérification de l'existence de l'utilisateur {user_id}...")
    response = requests.get(f"{API_BASE_URL}/api/users", headers={"Authorization": f"Bearer {admin_token}"})
    if response.status_code == 200:
        users = response.json()
        user_found = False
        for user in users:
            if str(user.get("_id")) == str(user_id):
                user_found = True
                print(f"✅ Utilisateur trouvé:")
                print(f"   - Nom: {user.get('name')}")
                print(f"   - Email: {user.get('email')}")
                print(f"   - Rôle: {user.get('role')}")
                print(f"   - Téléphone: {user.get('telephone')}")
                print(f"   - Statut: {user.get('statut')}")
                break
        
        if not user_found:
            print(f"❌ Utilisateur {user_id} non trouvé dans la base de données")
    else:
        print(f"❌ Erreur lors de la récupération des utilisateurs: {response.status_code}")

if __name__ == "__main__":
    verifier_offres_utilisateur()
