import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
from bson.objectid import ObjectId

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# Configuration sécurisée
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority")

# MongoDB
client = MongoClient(MONGO_URI)
db = client.appels_doffres_db
sources_col = db.appels_doffres_sourcess  # Collection avec double 's' comme dans votre base
users_col = db.users

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/admin")
def admin():
    return render_template('admin.html')

@app.route("/login")
def login_page():
    return render_template('login.html')

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

    # Debug: afficher les catégories existantes
    all_categories = sources_col.distinct("categorie")
    print(f"Catégories trouvées dans la base: {all_categories}")

    return jsonify({
        "nationale": fetch_block("Nationale"),
        "internationale": fetch_block("Internationale"),
        "debug_categories": all_categories  # Pour debug
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
    
    # Réorganiser les ordres AVANT l'insertion
    new_order = data.get("order", 1)
    categorie = data.get("categorie")
    if new_order and categorie:
        reorganize_orders_on_insert(categorie, new_order)
    
    sources_col.insert_one(data)
    return jsonify({"message": "Source ajoutée"}), 201

# Fonctions pour réorganiser les ordres
def reorganize_orders_on_update(categorie, old_order, new_order, entity_id):
    """Réorganise les ordres lors de la modification"""
    if new_order == old_order:
        return  # Pas de changement d'ordre
    
    if new_order < old_order:
        # Décaler vers le haut : les entités entre new_order et old_order-1 montent de +1
        sources_col.update_many(
            {
                "categorie": categorie,
                "order": {"$gte": new_order, "$lt": old_order},
                "_id": {"$ne": ObjectId(entity_id)}
            },
            {"$inc": {"order": 1}}
        )
    else:
        # Décaler vers le bas : les entités entre old_order+1 et new_order descendent de -1
        sources_col.update_many(
            {
                "categorie": categorie,
                "order": {"$gt": old_order, "$lte": new_order},
                "_id": {"$ne": ObjectId(entity_id)}
            },
            {"$inc": {"order": -1}}
        )

def reorganize_orders_on_insert(categorie, new_order):
    """Réorganise les ordres lors de l'insertion - décale vers le bas"""
    print(f"DEBUG: Réorganisation insertion - Catégorie: '{categorie}', Nouvel ordre: {new_order}")
    
    # Compter les éléments qui seront affectés
    count_before = sources_col.count_documents({
        "categorie": categorie,
        "order": {"$gte": new_order}
    })
    print(f"DEBUG: {count_before} éléments seront décalés dans la catégorie '{categorie}'")
    
    result = sources_col.update_many(
        {
            "categorie": categorie,
            "order": {"$gte": new_order}
        },
        {"$inc": {"order": 1}}
    )
    
    print(f"DEBUG: {result.modified_count} éléments modifiés")

# Route PUT complète avec vérification auth
@app.route("/api/sources/<source_id>", methods=["PUT"])
def update_source(source_id):
    # Vérification auth
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
    if not data:
        return jsonify({"message": "Données manquantes"}), 400
    
    # Récupérer l'ancienne entité
    try:
        old_entity = sources_col.find_one({"_id": ObjectId(source_id)})
    except:
        return jsonify({"message": "ID invalide"}), 400
    
    if not old_entity:
        return jsonify({"message": "Entité non trouvée"}), 404
    
    old_order = old_entity.get("order", 0)
    new_order = data.get("order", old_order)
    old_categorie = old_entity.get("categorie")
    new_categorie = data.get("categorie")
    
    # Si changement de catégorie
    if old_categorie != new_categorie:
        # Réorganiser l'ancienne catégorie (décaler vers le haut)
        sources_col.update_many(
            {
                "categorie": old_categorie,
                "order": {"$gt": old_order},
                "_id": {"$ne": ObjectId(source_id)}
            },
            {"$inc": {"order": -1}}
        )
        # Réorganiser la nouvelle catégorie (décaler vers le bas)
        sources_col.update_many(
            {
                "categorie": new_categorie,
                "order": {"$gte": new_order},
                "_id": {"$ne": ObjectId(source_id)}
            },
            {"$inc": {"order": 1}}
        )
    else:
        # Même catégorie, réorganiser selon le nouvel ordre
        reorganize_orders_on_update(new_categorie, old_order, new_order, source_id)
    
    # Mettre à jour l'entité
    sources_col.update_one(
        {"_id": ObjectId(source_id)},
        {"$set": data}
    )
    return jsonify({"message": "Source mise à jour"}), 200
# Routes pour modification et suppression
# @app.route("/api/sources/<source_id>", methods=["PUT"])
# def update_source(source_id):
#     auth = request.headers.get("Authorization")
#     if not auth:
#         return jsonify({"message": "Token manquant"}), 401
#     try:
#         token = auth.split(" ")[1]
#         decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
#     except:
#         return jsonify({"message": "Token invalide"}), 401
#     if decoded.get("role") != "admin":
#         return jsonify({"message": "Accès refusé"}), 403

#     data = request.get_json()
#     if not all([data.get("nom_entite"), data.get("url"), data.get("categorie")]):
#         return jsonify({"message": "Champs manquants"}), 400
    
#     sources_col.update_one(
#         {"_id": ObjectId(source_id)},
#         {"$set": data}
#     )
#     return jsonify({"message": "Source mise à jour"}), 200

@app.route("/api/sources/<source_id>", methods=["DELETE"])
def delete_source(source_id):
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

    sources_col.delete_one({"_id": ObjectId(source_id)})
    return jsonify({"message": "Source supprimée"}), 200


# ===========================================
# GESTION DES UTILISATEURS (ADMIN) - ROUTES MANQUANTES
# ===========================================

def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"message": "Token manquant"}), 401
        try:
            token = auth.split(" ")[1]
            decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            if decoded.get("role") != "admin":
                return jsonify({"message": "Accès refusé - Admin requis"}), 403
        except:
            return jsonify({"message": "Token invalide"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/api/users", methods=["GET"])
@admin_required
def get_users():
    """Récupérer tous les utilisateurs (admin uniquement)"""
    try:
        # Vérifier la connexion à la base de données
        client.admin.command('ping')
        
        # Récupérer les utilisateurs
        users = list(users_col.find({}, {"password": 0}).sort("email", 1))
        
        # Convertir les ObjectId en string
        for user in users:
            user["_id"] = str(user["_id"])
        
        print(f"DEBUG: Récupéré {len(users)} utilisateurs depuis la base de données")
        return jsonify(users), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des utilisateurs: {str(e)}")
        return jsonify({"message": f"Erreur lors de la récupération des utilisateurs: {str(e)}"}), 500

@app.route("/api/users", methods=["POST"])
@admin_required
def create_user():
    """Créer un nouvel utilisateur (admin uniquement)"""
    data = request.get_json()
    if not data:
        return jsonify({"message": "Données manquantes"}), 400
    
    # Validation des champs requis
    required_fields = ["name", "email", "password", "role"]
    for field in required_fields:
        if not data.get(field):
            return jsonify({"message": f"Le champ {field} est requis"}), 400
    
    # Vérifier si l'email existe déjà
    if users_col.find_one({"email": data["email"]}):
        return jsonify({"message": "Un utilisateur avec cet email existe déjà"}), 400
    
    # Valider le rôle
    if data["role"] not in ["user", "admin"]:
        return jsonify({"message": "Rôle invalide"}), 400
    
    try:
        # Hasher le mot de passe
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        
        # Créer l'utilisateur
        user = {
            "name": data["name"],
            "email": data["email"],
            "password": hashed_password,
            "role": data["role"],
            "created_at": datetime.utcnow()
        }
        
        result = users_col.insert_one(user)
        user["_id"] = str(result.inserted_id)
        del user["password"]  # Ne pas retourner le mot de passe
        
        return jsonify({"message": "Utilisateur créé avec succès", "user": user}), 201
    except Exception as e:
        return jsonify({"message": "Erreur lors de la création de l'utilisateur"}), 500

@app.route("/api/users/<user_id>", methods=["GET"])
@admin_required
def get_user(user_id):
    """Récupérer un utilisateur spécifique (admin uniquement)"""
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/<user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    """Modifier un utilisateur (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que l'utilisateur existe
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Préparer les données à mettre à jour
        update_data = {}
        if "name" in data:
            update_data["name"] = data["name"]
        if "email" in data:
            # Vérifier que l'email n'est pas déjà utilisé par un autre utilisateur
            existing_user = users_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(user_id)}})
            if existing_user:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        if "role" in data:
            if data["role"] not in ["user", "admin"]:
                return jsonify({"message": "Rôle invalide"}), 400
            update_data["role"] = data["role"]
        if "password" in data and data["password"]:
            # Hacher le nouveau mot de passe
            hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
            update_data["password"] = hashed_password
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour l'utilisateur
        result = users_col.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Utilisateur mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    """Supprimer un utilisateur (admin uniquement)"""
    try:
        # Vérifier que l'utilisateur existe
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Empêcher la suppression du dernier admin
        if user.get("role") == "admin":
            admin_count = users_col.count_documents({"role": "admin"})
            if admin_count <= 1:
                return jsonify({"message": "Impossible de supprimer le dernier administrateur"}), 400
        
        # Supprimer l'utilisateur
        result = users_col.delete_one({"_id": ObjectId(user_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Utilisateur supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/stats", methods=["GET"])
@admin_required
def get_user_stats():
    """Statistiques des utilisateurs (admin uniquement)"""
    try:
        total_users = users_col.count_documents({})
        admin_users = users_col.count_documents({"role": "admin"})
        regular_users = users_col.count_documents({"role": "user"})
        
        return jsonify({
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": regular_users
        }), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération des statistiques: {str(e)}"}), 500

@app.route("/api/users/<user_id>/change-password", methods=["POST"])
@admin_required
def change_user_password(user_id):
    """Changer le mot de passe d'un utilisateur (admin uniquement)"""
    data = request.get_json()
    if not data:
        return jsonify({"message": "Données manquantes"}), 400
    
    # Validation des champs requis
    if not data.get("newPassword"):
        return jsonify({"message": "Le nouveau mot de passe est requis"}), 400
    
    if len(data["newPassword"]) < 6:
        return jsonify({"message": "Le nouveau mot de passe doit contenir au moins 6 caractères"}), 400
    
    try:
        # Récupérer l'utilisateur
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["newPassword"]).decode("utf-8")
        
        # Mettre à jour le mot de passe
        users_col.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "password": new_hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return jsonify({"message": "Mot de passe changé avec succès"}), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors du changement de mot de passe"}), 500

@app.route("/api/admin/change-password", methods=["POST"])
@admin_required
def admin_change_own_password():
    """Changer son propre mot de passe (admin uniquement)"""
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
    if not data:
        return jsonify({"message": "Données manquantes"}), 400
    
    # Validation des champs requis
    if not data.get("currentPassword"):
        return jsonify({"message": "Le mot de passe actuel est requis"}), 400
    
    if not data.get("newPassword"):
        return jsonify({"message": "Le nouveau mot de passe est requis"}), 400
    
    if len(data["newPassword"]) < 6:
        return jsonify({"message": "Le nouveau mot de passe doit contenir au moins 6 caractères"}), 400
    
    try:
        # Récupérer l'utilisateur admin
        user = users_col.find_one({"_id": ObjectId(decoded.get("user_id"))})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier le mot de passe actuel
        if not bcrypt.check_password_hash(user["password"], data["currentPassword"]):
            return jsonify({"message": "Mot de passe actuel incorrect"}), 400
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["newPassword"]).decode("utf-8")
        
        # Mettre à jour le mot de passe
        users_col.update_one(
            {"_id": ObjectId(decoded.get("user_id"))},
            {
                "$set": {
                    "password": new_hashed_password,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        return jsonify({"message": "Mot de passe changé avec succès"}), 200
    except Exception as e:
        return jsonify({"message": "Erreur lors du changement de mot de passe"}), 500

# ===========================================
# ROUTES DE TEST
# ===========================================

@app.route("/api/test", methods=["GET"])
def test_api():
    return jsonify({"status": "API OK", "message": "Backend fonctionne correctement"})

# @app.route("/api/users-public", methods=["GET"])
# def get_users_public():
#     """Route publique pour tester (TEMPORAIRE - À SUPPRIMER EN PRODUCTION)"""
#     try:
#         users = list(users_col.find({}, {"password": 0}).sort("email", 1))
#         for user in users:
#             user["_id"] = str(user["_id"])
#         return jsonify({"users": users, "count": len(users)})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/api/debug", methods=["GET"])
# def debug_info():
#     """Route de diagnostic pour Railway"""
#     try:
#         # Test de connexion MongoDB
#         client.admin.command('ping')
#         mongo_status = "Connected"
#     except Exception as e:
#         mongo_status = f"Error: {str(e)}"
    
#     try:
#         # Compter les utilisateurs
#         user_count = users_col.count_documents({})
#         users_status = f"Found {user_count} users"
#     except Exception as e:
#         users_status = f"Error: {str(e)}"
    
#     try:
#         # Compter les sources
#         sources_count = sources_col.count_documents({})
#         sources_status = f"Found {sources_count} sources"
#     except Exception as e:
#         sources_status = f"Error: {str(e)}"
    
#     return jsonify({
#         "status": "Debug Info",
#         "mongo_uri": MONGO_URI[:50] + "..." if len(MONGO_URI) > 50 else MONGO_URI,
#         "mongo_status": mongo_status,
#         "users_status": users_status,
#         "sources_status": sources_status,
#         "jwt_secret_set": bool(app.config["SECRET_KEY"]),
#         "environment": {
#             "PORT": os.getenv("PORT", "Not set"),
#             "JWT_SECRET": "Set" if os.getenv("JWT_SECRET") else "Not set",
#             "MONGO_URI": "Set" if os.getenv("MONGO_URI") else "Not set"
#         }
#     })

@app.route("/api/test-jwt", methods=["GET"])
def test_jwt():
    """Test de la configuration JWT"""
    try:
        # Test de génération de token
        test_token = jwt.encode({
            "test": "value",
            "exp": datetime.utcnow() + timedelta(minutes=1)
        }, app.config["SECRET_KEY"], algorithm="HS256")
        
        # Test de décodage
        decoded = jwt.decode(test_token, app.config["SECRET_KEY"], algorithms=["HS256"])
        
        return jsonify({
            "status": "JWT OK",
            "secret_key_set": bool(app.config["SECRET_KEY"]),
            "test_decoded": decoded
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ===========================================
# ROUTES PUBLIQUES POUR RAILWAY (TEMPORAIRE)
# ===========================================

@app.route("/api/users-public", methods=["GET"])
def get_users_public():
    """Route publique pour tester (TEMPORAIRE - À SUPPRIMER EN PRODUCTION)"""
    try:
        users = list(users_col.find({}, {"password": 0}).sort("email", 1))
        for user in users:
            user["_id"] = str(user["_id"])
        return jsonify({"users": users, "count": len(users)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Routes sans authentification pour Railway
@app.route("/api/users", methods=["GET"])
def get_users_no_auth():
    """Route utilisateurs sans authentification pour Railway (TEMPORAIRE)"""
    try:
        users = list(users_col.find({}, {"password": 0}).sort("email", 1))
        for user in users:
            user["_id"] = str(user["_id"])
        return jsonify(users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/users/stats", methods=["GET"])
def get_user_stats_no_auth():
    """Route statistiques sans authentification pour Railway (TEMPORAIRE)"""
    try:
        total_users = users_col.count_documents({})
        admin_users = users_col.count_documents({"role": "admin"})
        regular_users = users_col.count_documents({"role": "user"})
        
        return jsonify({
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": regular_users
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)


# from bcrypt import hashpw, gensalt

# password = "admin123"  # mot de passe en clair
# hashed = hashpw(password.encode('utf-8'), gensalt())
# print(hashed.decode())  # tu obtiens la version cryptée à mettre dans MongoDB

# password_user = "user123"
# hashed_user = hashpw(password_user.encode('utf-8'), gensalt())
# print(hashed_user.decode())