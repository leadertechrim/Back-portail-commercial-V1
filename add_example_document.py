#!/usr/bin/env python3
"""
Script pour ajouter un exemple de document dans la collection panier
"""

import os
from pymongo import MongoClient
from datetime import datetime

# Configuration MongoDB
MONGO_URI = "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

def add_example_documents():
    """Ajouter des exemples de documents dans la collection panier"""
    
    print("🔗 Connexion à MongoDB...")
    try:
        client = MongoClient(MONGO_URI)
        db = client.appels_doffres_db
        panier_col = db.panier
        
        # Test de connexion
        client.admin.command('ping')
        print("✅ Connexion MongoDB réussie")
        
        # Exemples de documents pour la collection panier
        example_documents = [
            {
                "title": "Appel d'offres - Développement Web",
                "type": "appel_offre",
                "description": "Développement d'une application web moderne avec React et Node.js",
                "quantity": 1,
                "price": 50000,
                "status": "pending",
                "client": "Entreprise ABC",
                "deadline": datetime(2024, 3, 15),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Consultation - Architecture Système",
                "type": "consultation",
                "description": "Consultation en architecture système pour migration cloud",
                "quantity": 2,
                "price": 15000,
                "status": "approved",
                "client": "Société XYZ",
                "deadline": datetime(2024, 2, 28),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Formation - React Avancé",
                "type": "formation",
                "description": "Formation en développement React avec hooks et context",
                "quantity": 1,
                "price": 8000,
                "status": "pending",
                "client": "Centre de Formation",
                "deadline": datetime(2024, 4, 10),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Maintenance - Application Legacy",
                "type": "maintenance",
                "description": "Maintenance et mise à jour d'une application legacy",
                "quantity": 1,
                "price": 25000,
                "status": "in_progress",
                "client": "Grande Entreprise",
                "deadline": datetime(2024, 5, 20),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "title": "Audit - Sécurité Informatique",
                "type": "audit",
                "description": "Audit de sécurité de l'infrastructure informatique",
                "quantity": 1,
                "price": 35000,
                "status": "completed",
                "client": "Banque Internationale",
                "deadline": datetime(2024, 1, 30),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        print(f"\n📝 Ajout de {len(example_documents)} documents d'exemple...")
        
        # Ajouter les documents
        result = panier_col.insert_many(example_documents)
        print(f"✅ {len(result.inserted_ids)} documents ajoutés avec succès")
        
        # Afficher les IDs des documents ajoutés
        print("\n📋 Documents ajoutés :")
        for i, doc_id in enumerate(result.inserted_ids):
            print(f"   {i+1}. ID: {doc_id}")
        
        # Vérifier le contenu de la collection
        print(f"\n🔍 Vérification de la collection panier...")
        total_docs = panier_col.count_documents({})
        print(f"   Total de documents dans la collection: {total_docs}")
        
        # Afficher quelques documents
        print(f"\n📊 Aperçu des documents :")
        for doc in panier_col.find().limit(3):
            print(f"   - {doc['title']} ({doc['type']}) - {doc['status']} - {doc['price']}€")
        
        print(f"\n✅ Exemples ajoutés avec succès dans la collection panier !")
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False
    
    finally:
        client.close()
    
    return True

def show_collection_stats():
    """Afficher les statistiques de la collection panier"""
    
    print("\n📊 Statistiques de la collection panier :")
    try:
        client = MongoClient(MONGO_URI)
        db = client.appels_doffres_db
        panier_col = db.panier
        
        # Statistiques générales
        total_docs = panier_col.count_documents({})
        print(f"   Total documents: {total_docs}")
        
        # Statistiques par type
        types = panier_col.distinct("type")
        print(f"   Types disponibles: {', '.join(types)}")
        
        for doc_type in types:
            count = panier_col.count_documents({"type": doc_type})
            print(f"   - {doc_type}: {count} documents")
        
        # Statistiques par statut
        statuses = panier_col.distinct("status")
        print(f"   Statuts disponibles: {', '.join(statuses)}")
        
        for status in statuses:
            count = panier_col.count_documents({"status": status})
            print(f"   - {status}: {count} documents")
        
        # Valeur totale
        pipeline = [
            {"$group": {"_id": None, "total_value": {"$sum": {"$multiply": ["$price", "$quantity"]}}}}
        ]
        result = list(panier_col.aggregate(pipeline))
        if result:
            total_value = result[0]["total_value"]
            print(f"   Valeur totale: {total_value:,}€")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'affichage des statistiques: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    print("🚀 Ajout d'exemples dans la collection panier")
    print("=" * 50)
    
    # Ajouter les exemples
    if add_example_documents():
        # Afficher les statistiques
        show_collection_stats()
    
    print("\n✅ Script terminé !")

