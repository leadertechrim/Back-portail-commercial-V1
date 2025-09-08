from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import os
app = Flask(__name__)

# Chaîne de connexion MongoDB Atlas (directement intégrée)
# Note : Pour une sécurité accrue en production, il est recommandé d'utiliser des variables d'environnement.
MONGO_URI = "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client.appels_doffres_db
collection = db.appels_doffres_sources

@app.route('/')
def home():
    """Route pour la page d'accueil. Affiche toutes les sources d'appels d'offres."""
    sources = list(collection.find({}).sort("nom_entite", 1))
    return render_template('index.html', sources=sources)

# @app.route('/recherche', methods=['GET'])
# def recherche():
#     """Route pour la recherche dynamique via JavaScript."""
#     query_param = request.args.get('q', '')
#     if query_param:
#         # Recherche insensible à la casse dans les noms et les catégories
#         results = list(collection.find(
#             {"$or": [
#                 {"nom_entite": {"$regex": query_param, "$options": "i"}},
#                 {"categorie": {"$regex": query_param, "$options": "i"}}
#             ]}
#         ))
#     else:
#         # Retourne une liste vide si la requête est vide
#         results = []
    
#     return jsonify(results)

@app.route('/recherche', methods=['GET'])
def recherche():
    """Route pour la recherche dynamique via JavaScript."""
    query_param = request.args.get('q', '')
    if query_param:
        # Recherche insensible à la casse
        results = list(collection.find(
            {"$or": [
                {"nom_entite": {"$regex": query_param, "$options": "i"}},
                {"categorie": {"$regex": query_param, "$options": "i"}}
            ]}
        ))
    else:
        results = []

    # Conversion des ObjectId en chaînes de caractères
    # C'est la ligne de code cruciale pour corriger l'erreur
    sanitized_results = []
    for result in results:
        # Convertit l'ObjectId en string pour qu'il soit sérialisable en JSON
        result['_id'] = str(result['_id'])
        sanitized_results.append(result)

    return jsonify(sanitized_results)


if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=8000)
