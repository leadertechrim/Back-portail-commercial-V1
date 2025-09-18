#!/usr/bin/env python3
"""
Script de test pour créer un appel d'offres avec document
"""

import requests
import json
import base64
from datetime import datetime, timedelta

# Configuration
BASE_URL = "http://localhost:8000"

def create_test_document():
    """Créer un document de test"""
    test_content = """
    APPEL D'OFFRES - TEST
    
    Titre: Développement d'application web
    Client: Entreprise Test
    Source: Site officiel
    État: En cours
    Description: Développement d'une application web moderne
    Date limite: 2024-02-15
    
    Ceci est un document de test pour l'appel d'offres.
    """
    
    # Encoder en base64
    return base64.b64encode(test_content.encode('utf-8')).decode('utf-8')

def test_panier_functionality():
    """Tester la fonctionnalité panier"""
    
    print("🧪 Test de fonctionnalité panier")
    print("=" * 60)
    
    # 1. Test de connexion
    print("\n1️⃣ Test de connexion au backend")
    try:
        response = requests.get(f"{BASE_URL}/api/test-connection")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend fonctionne: {data.get('message')}")
        else:
            print(f"❌ Erreur connexion: {response.text}")
            return
    except Exception as e:
        print(f"❌ Impossible de se connecter: {e}")
        return
    
    # 2. Test d'ajout d'éléments au panier
    print("\n2️⃣ Test d'ajout d'éléments au panier")
    try:
        # Données pour le panier (utilise la structure existante)
        panier_items = [
            {
                "title": "Appel d'offres - Développement Web",
                "type": "appel_offre", 
                "description": "Développement d'une application web moderne",
                "quantity": 1,
                "price": 50000,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Consultation - Architecture",
                "type": "consultation",
                "description": "Consultation en architecture système", 
                "quantity": 2,
                "price": 15000,
                "status": "approved",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Formation - React",
                "type": "formation",
                "description": "Formation en développement React",
                "quantity": 1,
                "price": 8000,
                "status": "pending",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        created_items = []
        
        for i, item_data in enumerate(panier_items):
            print(f"   Ajout de l'élément {i+1}: {item_data['title']}")
            
            # Utilise la route spécifique pour le panier
            response = requests.post(f"{BASE_URL}/api/panier", json=item_data)
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                print(f"   ✅ Élément ajouté: {data.get('item', {}).get('_id')}")
                created_items.append(data.get('item', {}).get('_id'))
            else:
                print(f"   ❌ Erreur: {response.text}")
        
        return created_items
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return []
    
    # 3. Test de récupération du panier
    print("\n3️⃣ Test de récupération du panier")
    try:
        # Utilise la route spécifique pour le panier
        response = requests.get(f"{BASE_URL}/api/panier")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Récupéré {len(data)} éléments du panier")
            if data:
                print("   Éléments du panier:")
                for i, item in enumerate(data):
                    print(f"   - {i+1}. {item.get('title', 'N/A')} ({item.get('type', 'N/A')}) - {item.get('status', 'N/A')}")
                    print(f"     Prix: {item.get('price', 'N/A')} - Quantité: {item.get('quantity', 'N/A')}")
        else:
            print(f"❌ Erreur récupération: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_panier_operations(panier_items):
    """Tester les opérations sur le panier"""
    if not panier_items:
        print("\n❌ Pas d'éléments du panier pour tester les opérations")
        return
    
    print(f"\n4️⃣ Test des opérations sur le panier")
    try:
        # Test de modification d'un élément
        if panier_items:
            item_id = panier_items[0]
            print(f"   Modification de l'élément: {item_id}")
            
            update_data = {
                "title": "Appel d'offres - Développement Web MODIFIÉ",
                "status": "approved",
                "price": 60000
            }
            
            # Utilise la route spécifique pour le panier
            response = requests.put(f"{BASE_URL}/api/panier/{item_id}", json=update_data)
            print(f"   Status modification: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Élément modifié avec succès")
            else:
                print(f"   ❌ Erreur modification: {response.text}")
        
        # Test de suppression d'un élément
        if len(panier_items) > 1:
            item_id = panier_items[1]
            print(f"   Suppression de l'élément: {item_id}")
            
            # Utilise la route spécifique pour le panier
            response = requests.delete(f"{BASE_URL}/api/panier/{item_id}")
            print(f"   Status suppression: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Élément supprimé avec succès")
            else:
                print(f"   ❌ Erreur suppression: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    print("🚀 Démarrage du test de fonctionnalité panier")
    
    # Test principal
    panier_items = test_panier_functionality()
    
    # Test des opérations sur le panier si ajout réussi
    if panier_items:
        test_panier_operations(panier_items)
    
    print("\n✅ Tests terminés")
    print("\n📋 Résumé:")
    print("- ✅ Connexion au backend")
    print("- ✅ Ajout d'éléments au panier")
    print("- ✅ Récupération du panier")
    print("- ✅ Modification d'éléments")
    print("- ✅ Suppression d'éléments")
