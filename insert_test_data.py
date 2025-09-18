#!/usr/bin/env python3
"""
Script pour insérer des données de test dans les nouvelles collections
"""

import os
from pymongo import MongoClient
from datetime import datetime

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority")

def insert_test_data():
    """Insérer des données de test dans les collections"""
    try:
        # Connexion à MongoDB
        client = MongoClient(MONGO_URI)
        db = client.appels_doffres_db
        
        print("=== INSERTION DES DONNÉES DE TEST ===")
        
        # Données de test pour les clients
        clients_data = [
            {
                "raison_sociale": "Ministère de la Transformation numérique",
                "nom_prenom": "Ahmed Ould Mohamed",
                "telephone": "+22245213456",
                "whatsapp": "+22245213456",
                "email": "contact@numerique.gov.mr",
                "adresse": "Avenue Gamal Abdel Nasser, Nouakchott",
                "note_commentaire": "Client stratégique du secteur public, relation à long terme.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "raison_sociale": "Banque Centrale de Mauritanie",
                "nom_prenom": "Fatima Mint Ahmed",
                "telephone": "+22245213457",
                "whatsapp": "+22245213457",
                "email": "fatima@bcm.mr",
                "adresse": "Avenue de l'Indépendance, Nouakchott",
                "note_commentaire": "Client institutionnel important.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Données de test pour les partenaires
        partenaires_data = [
            {
                "raison_sociale": "TechAfrica Solutions",
                "nom_prenom": "Fatou Diop",
                "telephone": "+221776543210",
                "whatsapp": "+221776543210",
                "email": "fatou.diop@techafrica.com",
                "adresse": "Immeuble Africa Tower, Dakar",
                "note_commentaire": "Partenaire fiable pour les projets digitaux transfrontaliers.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "raison_sociale": "Digital Solutions SARL",
                "nom_prenom": "Mohamed Ould Salem",
                "telephone": "+22245213458",
                "whatsapp": "+22245213458",
                "email": "mohamed@digitalsolutions.mr",
                "adresse": "Zone Industrielle, Nouakchott",
                "note_commentaire": "Partenaire local spécialisé en solutions web.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Données de test pour les personnels
        personnels_data = [
            {
                "nom_prenom": "Mohamed Salem",
                "telephone": "+22236457890",
                "whatsapp": "+22236457890",
                "email": "m.salem@entreprise.mr",
                "adresse": "Tevragh Zeina, Nouakchott",
                "note_commentaire": "Très professionnel, ponctuel et compétent.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "nom_prenom": "Aicha Mint Mohamed",
                "telephone": "+22236457891",
                "whatsapp": "+22236457891",
                "email": "aicha@entreprise.mr",
                "adresse": "El Mina, Nouakchott",
                "note_commentaire": "Développeuse expérimentée, excellente communication.",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        # Insérer les clients
        print("Insertion des clients...")
        clients_col = db.clients
        result_clients = clients_col.insert_many(clients_data)
        print(f"✓ {len(result_clients.inserted_ids)} clients insérés")
        
        # Insérer les partenaires
        print("Insertion des partenaires...")
        partenaires_col = db.partenaires
        result_partenaires = partenaires_col.insert_many(partenaires_data)
        print(f"✓ {len(result_partenaires.inserted_ids)} partenaires insérés")
        
        # Insérer les personnels
        print("Insertion des personnels...")
        personnels_col = db.personnels
        result_personnels = personnels_col.insert_many(personnels_data)
        print(f"✓ {len(result_personnels.inserted_ids)} personnels insérés")
        
        # Vérifier les insertions
        print("\n=== VÉRIFICATION DES INSERTIONS ===")
        print(f"Clients: {clients_col.count_documents({})}")
        print(f"Partenaires: {partenaires_col.count_documents({})}")
        print(f"Personnels: {personnels_col.count_documents({})}")
        
        client.close()
        print("\n✅ Données de test insérées avec succès!")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion: {e}")

if __name__ == "__main__":
    insert_test_data()
