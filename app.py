from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

app.config["SECRET_KEY"] = "SECRET_SUPER_CLE_CHANGE_LA"

# MongoDB
MONGO_URI = "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(MONGO_URI)
db = client.appels_doffres_db
sources_col = db.appels_doffres_sourcess
users_col = db.users

# Routes sources
# @app.route("/api/sources", methods=["GET"])
# def get_sources():
#     sources = list(sources_col.find({}).sort("nom_entite", 1))
#     for s in sources:
#         s["_id"] = str(s["_id"])
#         s["nom_entite"] = str(s.get("nom_entite", ""))
#         s["categorie"] = str(s.get("categorie", ""))
#         s["url"] = str(s.get("url", ""))
#     return jsonify(sources)

@app.route("/api/sources", methods=["GET"])
def get_sources():
    categorie = request.args.get("categorie")
    query = {}
    if categorie:
        query["categorie"] = categorie

    sources = list(sources_col.find(query).sort([("order", 1), ("nom_entite", 1)]))
    for s in sources:
        s["_id"] = str(s["_id"])
        s["nom_entite"] = str(s.get("nom_entite", ""))
        s["categorie"] = str(s.get("categorie", ""))
        s["url"] = str(s.get("url", ""))
        if "order" in s:
            try:
                s["order"] = int(s["order"])
            except Exception:
                pass
    return jsonify(sources)

# @app.route("/api/recherche", methods=["GET"])
# def recherche():
#     q = request.args.get("q", "")
#     results = list(sources_col.find({
#         "$or": [
#             {"nom_entite": {"$regex": q, "$options": "i"}},
#             {"categorie": {"$regex": q, "$options": "i"}}
#         ]
#     }))
#     for r in results:
#         r["_id"] = str(r["_id"])
#         r["nom_entite"] = str(r.get("nom_entite", ""))
#         r["categorie"] = str(r.get("categorie", ""))
#         r["url"] = str(r.get("url", ""))
#     return jsonify(results)
@app.route("/api/recherche", methods=["GET"])
def recherche():
    q = request.args.get("q", "")
    results = list(sources_col.find({
        "$or": [
            {"nom_entite": {"$regex": q, "$options": "i"}},
            {"categorie": {"$regex": q, "$options": "i"}}
        ]
    }).sort([("order", 1), ("nom_entite", 1)]))

    for r in results:
        r["_id"] = str(r["_id"])
        r["nom_entite"] = str(r.get("nom_entite", ""))
        r["categorie"] = str(r.get("categorie", ""))
        r["url"] = str(r.get("url", ""))
        if "order" in r:
            try:
                r["order"] = int(r["order"])
            except Exception:
                pass
    return jsonify(results)


@app.route("/api/sources/grouped", methods=["GET"])
def get_sources_grouped():
    def fetch_block(cat):
        docs = list(sources_col.find({"categorie": cat}).sort([("order", 1), ("nom_entite", 1)]))
        for d in docs:
            d["_id"] = str(d["_id"])
            d["nom_entite"] = str(d.get("nom_entite", ""))
            d["categorie"] = str(d.get("categorie", ""))
            d["url"] = str(d.get("url", ""))
            if "order" in d:
                try:
                    d["order"] = int(d["order"])
                except Exception:
                    pass
        return docs

    return jsonify({
        "nationale": fetch_block("Nationale"),
        "internationale": fetch_block("Internationale")
    })    
# Routes Auth
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    name = data.get("name")
    role = data.get("role", "user")

    if users_col.find_one({"email": email}):
        return jsonify({"message": "Utilisateur déjà existant"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = {"email": email, "password": hashed, "name": name, "role": role}
    users_col.insert_one(user)
    return jsonify({"message": "Utilisateur créé"}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"message": "Utilisateur non trouvé"}), 404

    if bcrypt.check_password_hash(user["password"], password):
        token = jwt.encode({
            "user_id": str(user["_id"]),
            "role": user.get("role", "user"),
            "exp": datetime.utcnow() + timedelta(hours=6)
        }, app.config["SECRET_KEY"], algorithm="HS256")
        return jsonify({"token": token, "role": user.get("role", "user"), "name": user.get("name")})
    else:
        return jsonify({"message": "Mot de passe incorrect"}), 401

# Ajouter source (admin)


@app.route("/api/sources", methods=["POST"])
def add_source():
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"message": "Token manquant"}), 401
    try:
        token = auth.split(" ")[1]
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except:
        return jsonify({"message": "Token invalide"}), 401
    if decoded.get("role") != "admin":
        return jsonify({"message": "Accès refusé"}), 403

    data = request.get_json()
    if not all([data.get("nom_entite"), data.get("url"), data.get("categorie")]):
        return jsonify({"message": "Champs manquants"}), 400
    sources_col.insert_one(data)
    return jsonify({"message": "Source ajoutée"}), 201




if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8000)


# from bcrypt import hashpw, gensalt

# password = "admin123"  # mot de passe en clair
# hashed = hashpw(password.encode('utf-8'), gensalt())
# print(hashed.decode())  # tu obtiens la version cryptée à mettre dans MongoDB

# password_user = "user123"
# hashed_user = hashpw(password_user.encode('utf-8'), gensalt())
# print(hashed_user.decode())