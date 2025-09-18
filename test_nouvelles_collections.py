#!/usr/bin/env python3
"""
Script de test pour vérifier les nouvelles collections (Clients, Partenaires, Personnels)
"""

import requests
import json
from datetime import datetime

API_BASE_URL = "http://127.0.0.1:8000"

def test_api_connection():
    """Tester la connexion à l'API"""
    try:
        response = requests.get(f"{API_BASE_URL}/api/test")
        print(f"✓ Connexion API: {response.status_code}")
        if response.status_code == 200:
            print(f"  Réponse: {response.json()}")
        return True
    except Exception as e:
        print(f"✗ Erreur de connexion API: {e}")
        return False

def test_clients():
    """Tester les routes des clients"""
    print("\n=== TEST CLIENTS ===")
    
    # Test GET /api/clients
    try:
        response = requests.get(f"{API_BASE_URL}/api/clients")
        print(f"GET /api/clients: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Nombre de clients: {len(data)}")
            if data:
                print(f"  Premier client: {data[0]}")
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur GET clients: {e}")

def test_partenaires():
    """Tester les routes des partenaires"""
    print("\n=== TEST PARTENAIRES ===")
    
    # Test GET /api/partenaires
    try:
        response = requests.get(f"{API_BASE_URL}/api/partenaires")
        print(f"GET /api/partenaires: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Nombre de partenaires: {len(data)}")
            if data:
                print(f"  Premier partenaire: {data[0]}")
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur GET partenaires: {e}")

def test_personnels():
    """Tester les routes des personnels"""
    print("\n=== TEST PERSONNELS ===")
    
    # Test GET /api/personnels
    try:
        response = requests.get(f"{API_BASE_URL}/api/personnels")
        print(f"GET /api/personnels: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"  Nombre de personnels: {len(data)}")
            if data:
                print(f"  Premier personnel: {data[0]}")
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur GET personnels: {e}")

def test_create_client():
    """Tester la création d'un client"""
    print("\n=== TEST CRÉATION CLIENT ===")
    
    client_data = {
        "raison_sociale": "Test Client SA",
        "nom_prenom": "Test User",
        "telephone": "+22212345678",
        "whatsapp": "+22212345678",
        "email": "test@client.com",
        "adresse": "Adresse Test",
        "note_commentaire": "Client de test"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/clients",
            json=client_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/clients: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"  Client créé: {data}")
            return data.get('client', {}).get('_id')
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur création client: {e}")
    
    return None

def test_create_partenaire():
    """Tester la création d'un partenaire"""
    print("\n=== TEST CRÉATION PARTENAIRE ===")
    
    partenaire_data = {
        "raison_sociale": "Test Partenaire SARL",
        "nom_prenom": "Test Partner",
        "telephone": "+22287654321",
        "whatsapp": "+22287654321",
        "email": "test@partenaire.com",
        "adresse": "Adresse Partenaire Test",
        "note_commentaire": "Partenaire de test"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/partenaires",
            json=partenaire_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/partenaires: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"  Partenaire créé: {data}")
            return data.get('partenaire', {}).get('_id')
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur création partenaire: {e}")
    
    return None

def test_create_personnel():
    """Tester la création d'un personnel"""
    print("\n=== TEST CRÉATION PERSONNEL ===")
    
    personnel_data = {
        "nom_prenom": "Test Personnel",
        "telephone": "+22211223344",
        "whatsapp": "+22211223344",
        "email": "test@personnel.com",
        "adresse": "Adresse Personnel Test",
        "note_commentaire": "Personnel de test"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/personnels",
            json=personnel_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"POST /api/personnels: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"  Personnel créé: {data}")
            return data.get('personnel', {}).get('_id')
        else:
            print(f"  Erreur: {response.text}")
    except Exception as e:
        print(f"✗ Erreur création personnel: {e}")
    
    return None

def main():
    print("=== TEST DES NOUVELLES COLLECTIONS ===")
    print(f"URL de base: {API_BASE_URL}")
    print(f"Date: {datetime.now()}")
    
    # Test de connexion
    if not test_api_connection():
        print("❌ Impossible de se connecter à l'API")
        return
    
    # Test des collections existantes
    test_clients()
    test_partenaires()
    test_personnels()
    
    # Test de création
    client_id = test_create_client()
    partenaire_id = test_create_partenaire()
    personnel_id = test_create_personnel()
    
    # Test de récupération après création
    if client_id or partenaire_id or personnel_id:
        print("\n=== VÉRIFICATION APRÈS CRÉATION ===")
        test_clients()
        test_partenaires()
        test_personnels()
    
    print("\n=== TEST TERMINÉ ===")

if __name__ == "__main__":
    main()
