#!/usr/bin/env python3
"""
Script pour vérifier les collections MongoDB et leurs données
"""

import os
from pymongo import MongoClient
from bson.objectid import ObjectId

# Configuration MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority")

def check_collections():
    """Vérifier les collections et leurs données"""
    try:
        # Connexion à MongoDB
        client = MongoClient(MONGO_URI)
        db = client.appels_doffres_db
        
        print("=== VÉRIFICATION DES COLLECTIONS MONGODB ===")
        print(f"Base de données: {db.name}")
        
        # Lister toutes les collections
        collections = db.list_collection_names()
        print(f"\nCollections disponibles: {collections}")
        
        # Vérifier les nouvelles collections
        new_collections = ['clients', 'partenaires', 'personnels']
        
        for collection_name in new_collections:
            print(f"\n--- Collection: {collection_name} ---")
            collection = db[collection_name]
            
            # Compter les documents
            count = collection.count_documents({})
            print(f"Nombre de documents: {count}")
            
            if count > 0:
                # Récupérer le premier document
                first_doc = collection.find_one()
                print(f"Premier document:")
                for key, value in first_doc.items():
                    if key == '_id':
                        print(f"  {key}: {value}")
                    else:
                        print(f"  {key}: {value}")
                
                # Récupérer tous les documents
                all_docs = list(collection.find())
                print(f"\nTous les documents ({len(all_docs)}):")
                for i, doc in enumerate(all_docs):
                    print(f"  Document {i+1}:")
                    for key, value in doc.items():
                        if key == '_id':
                            print(f"    {key}: {value}")
                        else:
                            print(f"    {key}: {value}")
            else:
                print("Aucun document trouvé")
        
        # Vérifier la collection users pour voir les champs
        print(f"\n--- Collection: users ---")
        users_collection = db.users
        user_count = users_collection.count_documents({})
        print(f"Nombre d'utilisateurs: {user_count}")
        
        if user_count > 0:
            first_user = users_collection.find_one()
            print(f"Premier utilisateur:")
            for key, value in first_user.items():
                if key == '_id':
                    print(f"  {key}: {value}")
                elif key == 'password':
                    print(f"  {key}: [HIDDEN]")
                else:
                    print(f"  {key}: {value}")
        
        client.close()
        print("\n=== VÉRIFICATION TERMINÉE ===")
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")

if __name__ == "__main__":
    check_collections()
