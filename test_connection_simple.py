#!/usr/bin/env python3
"""
Test simple de connexion au backend
"""

import requests
import time

def test_backend_connection():
    """Tester la connexion au backend"""
    
    print("🔗 Test de connexion au backend...")
    
    # Attendre un peu pour que le backend démarre
    print("⏳ Attente du démarrage du backend...")
    time.sleep(2)
    
    # Test de connexion de base
    try:
        response = requests.get("http://localhost:8000/api/test-connection", timeout=5)
        print(f"✅ Test de connexion: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Message: {data.get('message')}")
            print(f"   Port: {data.get('port')}")
        else:
            print(f"   Erreur: {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter au backend")
        print("   Vérifiez que le backend tourne sur le port 8000")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    # Test spécifique du panier
    try:
        response = requests.get("http://localhost:8000/api/panier/test", timeout=5)
        print(f"✅ Test panier: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Message: {data.get('message')}")
            print(f"   Total items: {data.get('total_items')}")
        else:
            print(f"   Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Erreur test panier: {e}")
        return False
    
    # Test de récupération du panier
    try:
        response = requests.get("http://localhost:8000/api/panier", timeout=5)
        print(f"✅ Test récupération panier: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Nombre d'éléments: {len(data)}")
            if data:
                print("   Premier élément:")
                print(f"     - {data[0].get('title', 'N/A')}")
        else:
            print(f"   Erreur: {response.text}")
    except Exception as e:
        print(f"❌ Erreur récupération panier: {e}")
        return False
    
    print("\n✅ Tous les tests de connexion ont réussi !")
    return True

if __name__ == "__main__":
    print("🚀 Démarrage des tests de connexion")
    print("=" * 40)
    
    if test_backend_connection():
        print("\n🎉 Backend opérationnel !")
    else:
        print("\n❌ Problème de connexion détecté")
        print("\n💡 Solutions possibles:")
        print("   1. Vérifiez que le backend tourne: python app.py")
        print("   2. Vérifiez le port (8000)")
        print("   3. Vérifiez les erreurs dans le terminal du backend")

