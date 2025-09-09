# from flask import Flask, render_template, request, jsonify
# from pymongo import MongoClient
# import os
# app = Flask(__name__)


# MONGO_URI = "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
# client = MongoClient(MONGO_URI)
# db = client.appels_doffres_db
# collection = db.appels_doffres_sources

# @app.route('/')
# def home():
#     """Route pour la page d'accueil. Affiche toutes les sources d'appels d'offres."""
#     sources = list(collection.find({}).sort("nom_entite", 1))
#     return render_template('index.html', sources=sources)


# @app.route('/recherche', methods=['GET'])
# def recherche():
#     """Route pour la recherche dynamique via JavaScript."""
#     query_param = request.args.get('q', '')
#     if query_param:
#         results = list(collection.find(
#             {"$or": [
#                 {"nom_entite": {"$regex": query_param, "$options": "i"}},
#                 {"categorie": {"$regex": query_param, "$options": "i"}}
#             ]}
#         ))
#     else:
#         results = []


#     sanitized_results = []
#     for result in results:
#         result['_id'] = str(result['_id'])
#         sanitized_results.append(result)

#     return jsonify(sanitized_results)


# if __name__ == "__main__":
#     app.run(debug=True, host='127.0.0.1', port=8000)
# backend/app.py
import os
from functools import wraps
from datetime import datetime, timedelta

from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
import jwt
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv

load_dotenv()  # charge variables d'environnement depuis .env

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# config
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PROD")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "appels_doffres_db")
TOKEN_EXP_HOURS = int(os.getenv("TOKEN_EXP_HOURS", "6"))

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
sources_col = db["appels_doffres_sources"]
users_col = db["users"]

# ---------------------------
# Helpers / Décorateurs
# ---------------------------
def decode_token_from_header():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header:
        return None, ("Token manquant", 401)
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None, ("Format d'autorisation invalide", 401)
    token = parts[1]
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return decoded, None
    except jwt.ExpiredSignatureError:
        return None, ("Token expiré", 401)
    except Exception:
        return None, ("Token invalide", 401)

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        decoded, err = decode_token_from_header()
        if err:
            msg, code = err
            return jsonify({"message": msg}), code
        if decoded.get("role") != "admin":
            return jsonify({"message": "Accès refusé, admin uniquement"}), 403
        return f(*args, **kwargs)
    return wrapper

# ---------------------------
# Routes Sources (public)
# ---------------------------
@app.route("/api/sources", methods=["GET"])
def get_sources():
    docs = list(sources_col.find({}).sort("nom_entite", 1))
    for d in docs:
        d["_id"] = str(d["_id"])
    return jsonify(docs), 200

@app.route("/api/recherche", methods=["GET"])
def recherche():
    q = request.args.get("q", "")
    if not q:
        return jsonify([]), 200
    results = list(sources_col.find(
        {"$or": [
            {"nom_entite": {"$regex": q, "$options": "i"}},
            {"categorie": {"$regex": q, "$options": "i"}}
        ]}
    ))
    for r in results:
        r["_id"] = str(r["_id"])
    return jsonify(results), 200

# ---------------------------
# Auth
# ---------------------------
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    name = data.get("name", "")
    role = data.get("role", "user")
    if not email or not password:
        return jsonify({"message": "email et password requis"}), 400
    if users_col.find_one({"email": email}):
        return jsonify({"message": "Utilisateur déjà existant"}), 400
    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user_doc = {"email": email, "password": hashed, "name": name, "role": role}
    res = users_col.insert_one(user_doc)
    return jsonify({"message": "Utilisateur créé", "id": str(res.inserted_id)}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "email et password requis"}), 400
    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"message": "Utilisateur non trouvé"}), 404
    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"message": "Mot de passe incorrect"}), 401

    payload = {
        "user_id": str(user["_id"]),
        "email": user["email"],
        "role": user.get("role", "user"),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXP_HOURS)
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return jsonify({
        "token": token,
        "user": {"id": str(user["_id"]), "email": user["email"], "name": user.get("name", ""), "role": user.get("role", "user")}
    }), 200

# ---------------------------
# Admin - Ajouter source
# ---------------------------
@app.route("/api/sources", methods=["POST"])
@admin_required
def add_source():
    data = request.get_json() or {}
    nom_entite = data.get("nom_entite")
    url = data.get("url")
    categorie = data.get("categorie")
    if not nom_entite or not url or not categorie:
        return jsonify({"message": "nom_entite, url et categorie requis"}), 400
    new_doc = {"nom_entite": nom_entite, "url": url, "categorie": categorie}
    res = sources_col.insert_one(new_doc)
    return jsonify({"message": "Source ajoutée avec succès", "id": str(res.inserted_id)}), 201

# ---------------------------
# Utilitaires (optionnel) - afficher users (dev)
# ---------------------------
@app.route("/api/users", methods=["GET"])
def list_users():
    # Pour debug uniquement: caches/retirer en prod
    docs = list(users_col.find({}, {"password": 0}).sort("email", 1))
    for d in docs:
        d["_id"] = str(d["_id"])
    return jsonify(docs), 200

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=int(os.getenv("PORT", 8000)))
