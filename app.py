import os
import re
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
offres_col = db.offres
calls_for_tender_col = db.calls_for_tender
clients_col = db.Clients
partenaires_col = db.Partenaires
personnels_col = db.Personnels

@app.route("/")
def home():
    return render_template('index.html')

@app.route("/admin")
def admin():
    return render_template('admin.html')

@app.route("/login")
def login_page():
    return render_template('login.html')

# ===========================================
# FONCTIONS DE VALIDATION
# ===========================================

def validate_email(email):
    """Valider le format de l'email"""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Valider le mot de passe (minimum 6 caractères)"""
    return password and isinstance(password, str) and len(password) >= 6

def validate_telephone(telephone):
    """Valider le format du téléphone"""
    if not telephone:
        return True  # Optionnel
    if not isinstance(telephone, str):
        return False
    # Format international simple
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, telephone) is not None

def validate_statut(statut):
    """Valider le statut utilisateur"""
    if not statut:
        return True  # Optionnel
    valid_statuts = ["actif", "inactif", "suspendu"]
    return statut in valid_statuts

def validate_gerer(gerer):
    """Valider le champ gerer (boolean)"""
    return isinstance(gerer, bool)

def validate_panier_title(title):
    """Valider le titre du panier"""
    return title and isinstance(title, str) and len(title.strip()) > 0

def validate_panier_type(type_field):
    """Valider le type du panier"""
    valid_types = ["appel_offre", "consultation", "marché", "prestation"]
    return type_field in valid_types

def validate_panier_price(price):
    """Valider le prix du panier"""
    try:
        price_float = float(price)
        return price_float >= 0
    except (ValueError, TypeError):
        return False

def validate_panier_status(status):
    """Valider le statut du panier"""
    valid_statuses = ["Non préparé", "En préparation", "Envoyée"]
    return status in valid_statuses

def validate_panier_deadline(deadline):
    """Valider la date limite"""
    if not deadline:
        return True  # Optionnel
    try:
        datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False

def validate_panier_source(source):
    """Valider l'URL source"""
    if not source:
        return True  # Optionnel
    pattern = r'^https?://.+'
    return re.match(pattern, source) is not None

def validate_panier_note(note):
    """Valider les notes (liste d'URLs)"""
    if not note:
        return True  # Optionnel
    if not isinstance(note, list):
        return False
    pattern = r'^https?://.+'
    return all(re.match(pattern, url) for url in note if url)

def validate_panier_commentaire(commentaire):
    """Valider le commentaire"""
    return isinstance(commentaire, str)

def validate_raison_sociale(raison_sociale):
    """Valider la raison sociale"""
    return raison_sociale and isinstance(raison_sociale, str) and len(raison_sociale.strip()) > 0

def validate_nom_prenom(nom_prenom):
    """Valider le nom et prénom"""
    return nom_prenom and isinstance(nom_prenom, str) and len(nom_prenom.strip()) > 0

def validate_whatsapp(whatsapp):
    """Valider le numéro WhatsApp"""
    if not whatsapp:
        return True  # Optionnel
    if not isinstance(whatsapp, str):
        return False
    # Format international simple
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, whatsapp) is not None

def validate_adresse(adresse):
    """Valider l'adresse"""
    return isinstance(adresse, str)

def validate_note_commentaire(note_commentaire):
    """Valider la note/commentaire"""
    return isinstance(note_commentaire, str)

# ===========================================
# VALIDATIONS POUR LES OFFRES
# ===========================================

def validate_offre_intitulee(intitulee):
    """Valider l'intitulé de l'offre"""
    return isinstance(intitulee, str) and len(intitulee.strip()) > 0

def validate_offre_lien(lien):
    """Valider le lien de l'offre"""
    if not isinstance(lien, str):
        return False
    return len(lien.strip()) > 0

def validate_offre_client(client):
    """Valider le client de l'offre"""
    return isinstance(client, str) and len(client.strip()) > 0

def validate_offre_date_limite(date_limite):
    """Valider la date limite de l'offre"""
    if not isinstance(date_limite, str):
        return False
    try:
        from datetime import datetime
        datetime.fromisoformat(date_limite.replace('Z', '+00:00'))
        return True
    except:
        return False

def validate_offre_statut(statut):
    """Valider le statut de l'offre"""
    return statut in ["Non préparé", "En préparation", "Envoyée"]

def validate_offre_responsable_id(responsable_id):
    """Valider l'ID du responsable"""
    if not isinstance(responsable_id, str):
        return False
    try:
        ObjectId(responsable_id)
        return True
    except:
        return False

def validate_offre_documents(documents):
    """Valider les documents de l'offre"""
    return isinstance(documents, list) and all(isinstance(doc, str) for doc in documents)

def viewer_required(f):
    """Décorateur pour vérifier que l'utilisateur est au moins spectateur (peut voir mais pas modifier)"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"message": "Token manquant"}), 401
        try:
            token = auth.split(" ")[1]
            decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            role = decoded.get("role")
            if role not in ["admin", "user", "spectateur"]:
                return jsonify({"message": "Accès refusé - Rôle insuffisant"}), 403
            request.current_user = decoded
        except:
            return jsonify({"message": "Token invalide"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/api/sources", methods=["GET"])
@viewer_required
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
@viewer_required
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
    telephone = data.get("telephone", "")
    whatsapp = data.get("whatsapp", "")
    adresse = data.get("adresse", "")
    statut = data.get("statut", "actif")

    # Validations
    if not validate_email(email):
        return jsonify({"message": "Format d'email invalide"}), 400
    if not validate_password(password):
        return jsonify({"message": "Mot de passe doit contenir au moins 6 caractères"}), 400
    if not validate_telephone(telephone):
        return jsonify({"message": "Format de téléphone invalide"}), 400
    if not validate_whatsapp(whatsapp):
        return jsonify({"message": "Format de WhatsApp invalide"}), 400
    if not validate_adresse(adresse):
        return jsonify({"message": "Format d'adresse invalide"}), 400
    if not validate_statut(statut):
        return jsonify({"message": "Statut invalide"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"message": "Utilisateur déjà existant"}), 400

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = {
        "email": email, 
        "password": hashed, 
        "name": name, 
        "role": role,
        "telephone": telephone,
        "whatsapp": whatsapp,
        "adresse": adresse,
        "statut": statut,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
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
        return jsonify({
            "token": token, 
            "user_id": str(user["_id"]),
            "role": user.get("role", "user"), 
            "name": user.get("name"),
            "email": user.get("email"),
            "telephone": user.get("telephone", ""),
            "whatsapp": user.get("whatsapp", ""),
            "adresse": user.get("adresse", ""),
            "statut": user.get("statut", "actif")
        })
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

def optional_auth(f):
    """Décorateur pour authentification optionnelle (pour Railway)"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if auth:
            try:
                token = auth.split(" ")[1]
                decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                request.current_user = decoded
            except:
                request.current_user = None
        else:
            request.current_user = None
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/api/users", methods=["GET"])
@optional_auth
def get_users():
    """Récupérer tous les utilisateurs (avec authentification optionnelle pour Railway)"""
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
    
    # Validations
    if not validate_email(data["email"]):
        return jsonify({"message": "Format d'email invalide"}), 400
    if not validate_password(data["password"]):
        return jsonify({"message": "Mot de passe doit contenir au moins 6 caractères"}), 400
    
    # Vérifier si l'email existe déjà
    if users_col.find_one({"email": data["email"]}):
        return jsonify({"message": "Un utilisateur avec cet email existe déjà"}), 400
    
    # Valider le rôle
    if data["role"] not in ["user", "admin", "spectateur"]:
        return jsonify({"message": "Rôle invalide"}), 400
    
    # Validations des nouveaux champs
    telephone = data.get("telephone", "")
    whatsapp = data.get("whatsapp", "")
    adresse = data.get("adresse", "")
    statut = data.get("statut", "actif")
    
    if not validate_telephone(telephone):
        return jsonify({"message": "Format de téléphone invalide"}), 400
    if not validate_whatsapp(whatsapp):
        return jsonify({"message": "Format de WhatsApp invalide"}), 400
    if not validate_adresse(adresse):
        return jsonify({"message": "Format d'adresse invalide"}), 400
    if not validate_statut(statut):
        return jsonify({"message": "Statut invalide"}), 400
    
    try:
        # Hasher le mot de passe
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        
        # Créer l'utilisateur
        user = {
            "name": data["name"],
            "email": data["email"],
            "password": hashed_password,
            "role": data["role"],
            "telephone": telephone,
            "whatsapp": whatsapp,
            "adresse": adresse,
            "statut": statut,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
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
            if not validate_email(data["email"]):
                return jsonify({"message": "Format d'email invalide"}), 400
            # Vérifier que l'email n'est pas déjà utilisé par un autre utilisateur
            existing_user = users_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(user_id)}})
            if existing_user:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        if "role" in data:
            if data["role"] not in ["user", "admin", "spectateur"]:
                return jsonify({"message": "Rôle invalide"}), 400
            update_data["role"] = data["role"]
        if "password" in data and data["password"]:
            if not validate_password(data["password"]):
                return jsonify({"message": "Mot de passe doit contenir au moins 6 caractères"}), 400
            # Hacher le nouveau mot de passe
            hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
            update_data["password"] = hashed_password
        if "telephone" in data:
            if not validate_telephone(data["telephone"]):
                return jsonify({"message": "Format de téléphone invalide"}), 400
            update_data["telephone"] = data["telephone"]
        if "statut" in data:
            if not validate_statut(data["statut"]):
                return jsonify({"message": "Statut invalide"}), 400
            update_data["statut"] = data["statut"]
        if "whatsapp" in data:
            if not validate_whatsapp(data["whatsapp"]):
                return jsonify({"message": "Format de WhatsApp invalide"}), 400
            update_data["whatsapp"] = data["whatsapp"]
        if "adresse" in data:
            if not validate_adresse(data["adresse"]):
                return jsonify({"message": "Format d'adresse invalide"}), 400
            update_data["adresse"] = data["adresse"]
        
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
@optional_auth
def get_user_stats():
    """Statistiques des utilisateurs (avec authentification optionnelle pour Railway)"""
    try:
        total_users = users_col.count_documents({})
        admin_users = users_col.count_documents({"role": "admin"})
        regular_users = users_col.count_documents({"role": "user"})
        viewer_users = users_col.count_documents({"role": "spectateur"})
        
        return jsonify({
            "total_users": total_users,
            "admin_users": admin_users,
            "regular_users": regular_users,
            "viewer_users": viewer_users
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
    if not data.get("new_password"):
        return jsonify({"message": "Le nouveau mot de passe est requis"}), 400
    
    if not validate_password(data["new_password"]):
        return jsonify({"message": "Le nouveau mot de passe doit contenir au moins 6 caractères"}), 400
    
    try:
        # Récupérer l'utilisateur
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["new_password"]).decode("utf-8")
        
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
    if not data.get("current_password"):
        return jsonify({"message": "Le mot de passe actuel est requis"}), 400
    
    if not data.get("new_password"):
        return jsonify({"message": "Le nouveau mot de passe est requis"}), 400
    
    if not validate_password(data["new_password"]):
        return jsonify({"message": "Le nouveau mot de passe doit contenir au moins 6 caractères"}), 400
    
    try:
        # Récupérer l'utilisateur admin
        user = users_col.find_one({"_id": ObjectId(decoded.get("user_id"))})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier le mot de passe actuel
        if not bcrypt.check_password_hash(user["password"], data["current_password"]):
            return jsonify({"message": "Mot de passe actuel incorrect"}), 400
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["new_password"]).decode("utf-8")
        
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
# GESTION DES APPELS D'OFFRES
# ===========================================

@app.route("/api/calls-for-tender", methods=["GET"])
@viewer_required
def get_calls_for_tender():
    """Récupérer tous les appels d'offres"""
    try:
        calls = list(calls_for_tender_col.find().sort("created_at", -1))
        
        for call in calls:
            call["_id"] = str(call["_id"])
            # Convertir les dates
            if "deadline" in call and call["deadline"]:
                if hasattr(call["deadline"], 'isoformat'):
                    call["deadline"] = call["deadline"].isoformat()
            if "created_at" in call and call["created_at"]:
                if hasattr(call["created_at"], 'isoformat'):
                    call["created_at"] = call["created_at"].isoformat()
            if "updated_at" in call and call["updated_at"]:
                if hasattr(call["updated_at"], 'isoformat'):
                    call["updated_at"] = call["updated_at"].isoformat()
        
        return jsonify(calls), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des appels d'offres: {str(e)}")
        return jsonify([]), 200

@app.route("/api/calls-for-tender", methods=["POST"])
@optional_auth
def create_call_for_tender():
    """Créer un nouvel appel d'offres"""
    try:
        # Gérer les données FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            title = request.form.get("title")
            source = request.form.get("source")
            client = request.form.get("client")
            state = request.form.get("state")
            description = request.form.get("description", "")
            deadline = request.form.get("deadline")
            price = request.form.get("price", "0")
            type_field = request.form.get("type", "appel_offre")
            commentaire = request.form.get("commentaire", "")
            
            # Gérer les pièces jointes
            attachments = []
            for key, value in request.files.items():
                if key.startswith('attachment_'):
                    # Ici vous pouvez sauvegarder le fichier et stocker l'URL
                    # Pour l'instant, on stocke juste le nom du fichier
                    attachments.append(value.filename)
        else:
            # Gérer les données JSON
            data = request.get_json()
            if not data:
                return jsonify({"message": "Données manquantes"}), 400
            
            title = data.get("title")
            source = data.get("source")
            client = data.get("client")
            state = data.get("state")
            description = data.get("description", "")
            deadline = data.get("deadline")
            price = data.get("price", 0)
            type_field = data.get("type", "appel_offre")
            commentaire = data.get("commentaire", "")
            attachments = data.get("attachments", [])
        
        # Validation des champs requis
        if not title:
            return jsonify({"message": "Le titre est requis"}), 400
        if not client:
            return jsonify({"message": "Le client est requis"}), 400
        if not deadline:
            return jsonify({"message": "La date limite est requise"}), 400
        
        # Créer l'appel d'offres
        call_data = {
            "title": title,
            "source": source or "",
            "client": client,
            "state": state or "pending",
            "description": description,
            "deadline": datetime.fromisoformat(deadline.replace('Z', '+00:00')),
            "price": float(price),
            "type": type_field,
            "commentaire": commentaire,
            "attachments": attachments,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = calls_for_tender_col.insert_one(call_data)
        call_data["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Appel d'offres créé avec succès", "call": call_data}), 201
        
    except Exception as e:
        print(f"ERROR: Erreur lors de la création de l'appel d'offres: {str(e)}")
        return jsonify({"message": f"Erreur lors de la création: {str(e)}"}), 500

@app.route("/api/calls-for-tender/<call_id>", methods=["PUT"])
@optional_auth
def update_call_for_tender(call_id):
    """Modifier un appel d'offres"""
    try:
        # Vérifier que l'appel existe
        call = calls_for_tender_col.find_one({"_id": ObjectId(call_id)})
        if not call:
            return jsonify({"message": "Appel d'offres non trouvé"}), 404
        
        # Gérer les données FormData
        if request.content_type and 'multipart/form-data' in request.content_type:
            update_data = {}
            
            if request.form.get("title"):
                update_data["title"] = request.form.get("title")
            if request.form.get("source"):
                update_data["source"] = request.form.get("source")
            if request.form.get("client"):
                update_data["client"] = request.form.get("client")
            if request.form.get("state"):
                update_data["state"] = request.form.get("state")
            if request.form.get("description"):
                update_data["description"] = request.form.get("description")
            if request.form.get("deadline"):
                update_data["deadline"] = datetime.fromisoformat(request.form.get("deadline").replace('Z', '+00:00'))
            if request.form.get("price"):
                update_data["price"] = float(request.form.get("price"))
            if request.form.get("type"):
                update_data["type"] = request.form.get("type")
            if request.form.get("commentaire"):
                update_data["commentaire"] = request.form.get("commentaire")
            
            # Gérer les nouvelles pièces jointes
            new_attachments = []
            for key, value in request.files.items():
                if key.startswith('attachment_'):
                    new_attachments.append(value.filename)
            if new_attachments:
                update_data["attachments"] = new_attachments
        else:
            # Gérer les données JSON
            data = request.get_json()
            if not data:
                return jsonify({"message": "Données manquantes"}), 400
            
            update_data = {}
            if "title" in data:
                update_data["title"] = data["title"]
            if "source" in data:
                update_data["source"] = data["source"]
            if "client" in data:
                update_data["client"] = data["client"]
            if "state" in data:
                update_data["state"] = data["state"]
            if "description" in data:
                update_data["description"] = data["description"]
            if "deadline" in data:
                update_data["deadline"] = datetime.fromisoformat(data["deadline"].replace('Z', '+00:00'))
            if "price" in data:
                update_data["price"] = float(data["price"])
            if "type" in data:
                update_data["type"] = data["type"]
            if "commentaire" in data:
                update_data["commentaire"] = data["commentaire"]
            if "attachments" in data:
                update_data["attachments"] = data["attachments"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour l'appel d'offres
        result = calls_for_tender_col.update_one(
            {"_id": ObjectId(call_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Appel d'offres mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour: {str(e)}"}), 500

@app.route("/api/calls-for-tender/<call_id>", methods=["DELETE"])
@optional_auth
def delete_call_for_tender(call_id):
    """Supprimer un appel d'offres"""
    try:
        result = calls_for_tender_col.delete_one({"_id": ObjectId(call_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Appel d'offres supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Appel d'offres non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression: {str(e)}"}), 500

# ===========================================
# GESTION DES CLIENTS
# ===========================================

@app.route("/api/clients", methods=["GET"])
@viewer_required
def get_clients():
    """Récupérer tous les clients"""
    try:
        clients = list(clients_col.find().sort("raison_sociale", 1))
        
        for client in clients:
            client["_id"] = str(client["_id"])
        
        return jsonify(clients), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des clients: {str(e)}")
        return jsonify([]), 200

@app.route("/api/clients", methods=["POST"])
@admin_required
def create_client():
    """Créer un nouveau client (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Validation des champs requis
        required_fields = ["raison_sociale", "nom_prenom", "telephone", "email"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not validate_raison_sociale(data["raison_sociale"]):
            return jsonify({"message": "Raison sociale invalide"}), 400
        if not validate_nom_prenom(data["nom_prenom"]):
            return jsonify({"message": "Nom et prénom invalides"}), 400
        if not validate_telephone(data["telephone"]):
            return jsonify({"message": "Format de téléphone invalide"}), 400
        if not validate_email(data["email"]):
            return jsonify({"message": "Format d'email invalide"}), 400
        
        # Validations optionnelles
        whatsapp = data.get("whatsapp", "")
        adresse = data.get("adresse", "")
        note_commentaire = data.get("note_commentaire", "")
        
        if whatsapp and not validate_whatsapp(whatsapp):
            return jsonify({"message": "Format de WhatsApp invalide"}), 400
        if adresse and not validate_adresse(adresse):
            return jsonify({"message": "Format d'adresse invalide"}), 400
        if note_commentaire and not validate_note_commentaire(note_commentaire):
            return jsonify({"message": "Format de note/commentaire invalide"}), 400
        
        # Vérifier si l'email existe déjà
        if clients_col.find_one({"email": data["email"]}):
            return jsonify({"message": "Un client avec cet email existe déjà"}), 400
        
        # Créer le client
        client = {
            "raison_sociale": data["raison_sociale"],
            "nom_prenom": data["nom_prenom"],
            "telephone": data["telephone"],
            "whatsapp": whatsapp,
            "email": data["email"],
            "adresse": adresse,
            "note_commentaire": note_commentaire,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = clients_col.insert_one(client)
        client["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Client créé avec succès", "client": client}), 201
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la création du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["GET"])
@viewer_required
def get_client(client_id):
    """Récupérer un client spécifique"""
    try:
        client = clients_col.find_one({"_id": ObjectId(client_id)})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 404
        
        client["_id"] = str(client["_id"])
        return jsonify(client), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["PUT"])
@admin_required
def update_client(client_id):
    """Modifier un client (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que le client existe
        client = clients_col.find_one({"_id": ObjectId(client_id)})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 404
        
        # Préparer les données à mettre à jour
        update_data = {}
        
        if "raison_sociale" in data:
            if not validate_raison_sociale(data["raison_sociale"]):
                return jsonify({"message": "Raison sociale invalide"}), 400
            update_data["raison_sociale"] = data["raison_sociale"]
        
        if "nom_prenom" in data:
            if not validate_nom_prenom(data["nom_prenom"]):
                return jsonify({"message": "Nom et prénom invalides"}), 400
            update_data["nom_prenom"] = data["nom_prenom"]
        
        if "telephone" in data:
            if not validate_telephone(data["telephone"]):
                return jsonify({"message": "Format de téléphone invalide"}), 400
            update_data["telephone"] = data["telephone"]
        
        if "whatsapp" in data:
            if not validate_whatsapp(data["whatsapp"]):
                return jsonify({"message": "Format de WhatsApp invalide"}), 400
            update_data["whatsapp"] = data["whatsapp"]
        
        if "email" in data:
            if not validate_email(data["email"]):
                return jsonify({"message": "Format d'email invalide"}), 400
            # Vérifier que l'email n'est pas déjà utilisé par un autre client
            existing_client = clients_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(client_id)}})
            if existing_client:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        
        if "adresse" in data:
            if not validate_adresse(data["adresse"]):
                return jsonify({"message": "Format d'adresse invalide"}), 400
            update_data["adresse"] = data["adresse"]
        
        if "note_commentaire" in data:
            if not validate_note_commentaire(data["note_commentaire"]):
                return jsonify({"message": "Format de note/commentaire invalide"}), 400
            update_data["note_commentaire"] = data["note_commentaire"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour le client
        result = clients_col.update_one(
            {"_id": ObjectId(client_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Client mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["DELETE"])
@admin_required
def delete_client(client_id):
    """Supprimer un client (admin uniquement)"""
    try:
        result = clients_col.delete_one({"_id": ObjectId(client_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Client supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Client non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression du client: {str(e)}"}), 500

# ===========================================
# GESTION DES PARTENAIRES
# ===========================================

@app.route("/api/partenaires", methods=["GET"])
@viewer_required
def get_partenaires():
    """Récupérer tous les partenaires"""
    try:
        partenaires = list(partenaires_col.find().sort("raison_sociale", 1))
        
        for partenaire in partenaires:
            partenaire["_id"] = str(partenaire["_id"])
        
        return jsonify(partenaires), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des partenaires: {str(e)}")
        return jsonify([]), 200

@app.route("/api/partenaires", methods=["POST"])
@admin_required
def create_partenaire():
    """Créer un nouveau partenaire (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Validation des champs requis
        required_fields = ["raison_sociale", "nom_prenom", "telephone", "email"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not validate_raison_sociale(data["raison_sociale"]):
            return jsonify({"message": "Raison sociale invalide"}), 400
        if not validate_nom_prenom(data["nom_prenom"]):
            return jsonify({"message": "Nom et prénom invalides"}), 400
        if not validate_telephone(data["telephone"]):
            return jsonify({"message": "Format de téléphone invalide"}), 400
        if not validate_email(data["email"]):
            return jsonify({"message": "Format d'email invalide"}), 400
        
        # Validations optionnelles
        whatsapp = data.get("whatsapp", "")
        adresse = data.get("adresse", "")
        note_commentaire = data.get("note_commentaire", "")
        
        if whatsapp and not validate_whatsapp(whatsapp):
            return jsonify({"message": "Format de WhatsApp invalide"}), 400
        if adresse and not validate_adresse(adresse):
            return jsonify({"message": "Format d'adresse invalide"}), 400
        if note_commentaire and not validate_note_commentaire(note_commentaire):
            return jsonify({"message": "Format de note/commentaire invalide"}), 400
        
        # Vérifier si l'email existe déjà
        if partenaires_col.find_one({"email": data["email"]}):
            return jsonify({"message": "Un partenaire avec cet email existe déjà"}), 400
        
        # Créer le partenaire
        partenaire = {
            "raison_sociale": data["raison_sociale"],
            "nom_prenom": data["nom_prenom"],
            "telephone": data["telephone"],
            "whatsapp": whatsapp,
            "email": data["email"],
            "adresse": adresse,
            "note_commentaire": note_commentaire,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = partenaires_col.insert_one(partenaire)
        partenaire["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Partenaire créé avec succès", "partenaire": partenaire}), 201
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la création du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["GET"])
@viewer_required
def get_partenaire(partenaire_id):
    """Récupérer un partenaire spécifique"""
    try:
        partenaire = partenaires_col.find_one({"_id": ObjectId(partenaire_id)})
        if not partenaire:
            return jsonify({"message": "Partenaire non trouvé"}), 404
        
        partenaire["_id"] = str(partenaire["_id"])
        return jsonify(partenaire), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["PUT"])
@admin_required
def update_partenaire(partenaire_id):
    """Modifier un partenaire (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que le partenaire existe
        partenaire = partenaires_col.find_one({"_id": ObjectId(partenaire_id)})
        if not partenaire:
            return jsonify({"message": "Partenaire non trouvé"}), 404
        
        # Préparer les données à mettre à jour
        update_data = {}
        
        if "raison_sociale" in data:
            if not validate_raison_sociale(data["raison_sociale"]):
                return jsonify({"message": "Raison sociale invalide"}), 400
            update_data["raison_sociale"] = data["raison_sociale"]
        
        if "nom_prenom" in data:
            if not validate_nom_prenom(data["nom_prenom"]):
                return jsonify({"message": "Nom et prénom invalides"}), 400
            update_data["nom_prenom"] = data["nom_prenom"]
        
        if "telephone" in data:
            if not validate_telephone(data["telephone"]):
                return jsonify({"message": "Format de téléphone invalide"}), 400
            update_data["telephone"] = data["telephone"]
        
        if "whatsapp" in data:
            if not validate_whatsapp(data["whatsapp"]):
                return jsonify({"message": "Format de WhatsApp invalide"}), 400
            update_data["whatsapp"] = data["whatsapp"]
        
        if "email" in data:
            if not validate_email(data["email"]):
                return jsonify({"message": "Format d'email invalide"}), 400
            # Vérifier que l'email n'est pas déjà utilisé par un autre partenaire
            existing_partenaire = partenaires_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(partenaire_id)}})
            if existing_partenaire:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        
        if "adresse" in data:
            if not validate_adresse(data["adresse"]):
                return jsonify({"message": "Format d'adresse invalide"}), 400
            update_data["adresse"] = data["adresse"]
        
        if "note_commentaire" in data:
            if not validate_note_commentaire(data["note_commentaire"]):
                return jsonify({"message": "Format de note/commentaire invalide"}), 400
            update_data["note_commentaire"] = data["note_commentaire"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour le partenaire
        result = partenaires_col.update_one(
            {"_id": ObjectId(partenaire_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Partenaire mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["DELETE"])
@admin_required
def delete_partenaire(partenaire_id):
    """Supprimer un partenaire (admin uniquement)"""
    try:
        result = partenaires_col.delete_one({"_id": ObjectId(partenaire_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Partenaire supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Partenaire non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression du partenaire: {str(e)}"}), 500

# ===========================================
# GESTION DES PERSONNELS
# ===========================================

@app.route("/api/personnels", methods=["GET"])
@viewer_required
def get_personnels():
    """Récupérer tous les personnels"""
    try:
        personnels = list(personnels_col.find().sort("nom_prenom", 1))
        
        for personnel in personnels:
            personnel["_id"] = str(personnel["_id"])
        
        return jsonify(personnels), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des personnels: {str(e)}")
        return jsonify([]), 200

@app.route("/api/personnels", methods=["POST"])
@admin_required
def create_personnel():
    """Créer un nouveau personnel (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Validation des champs requis
        required_fields = ["nom_prenom", "telephone", "email"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not validate_nom_prenom(data["nom_prenom"]):
            return jsonify({"message": "Nom et prénom invalides"}), 400
        if not validate_telephone(data["telephone"]):
            return jsonify({"message": "Format de téléphone invalide"}), 400
        if not validate_email(data["email"]):
            return jsonify({"message": "Format d'email invalide"}), 400
        
        # Validations optionnelles
        whatsapp = data.get("whatsapp", "")
        adresse = data.get("adresse", "")
        note_commentaire = data.get("note_commentaire", "")
        
        if whatsapp and not validate_whatsapp(whatsapp):
            return jsonify({"message": "Format de WhatsApp invalide"}), 400
        if adresse and not validate_adresse(adresse):
            return jsonify({"message": "Format d'adresse invalide"}), 400
        if note_commentaire and not validate_note_commentaire(note_commentaire):
            return jsonify({"message": "Format de note/commentaire invalide"}), 400
        
        # Vérifier si l'email existe déjà
        if personnels_col.find_one({"email": data["email"]}):
            return jsonify({"message": "Un personnel avec cet email existe déjà"}), 400
        
        # Créer le personnel
        personnel = {
            "nom_prenom": data["nom_prenom"],
            "telephone": data["telephone"],
            "whatsapp": whatsapp,
            "email": data["email"],
            "adresse": adresse,
            "note_commentaire": note_commentaire,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = personnels_col.insert_one(personnel)
        personnel["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Personnel créé avec succès", "personnel": personnel}), 201
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la création du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["GET"])
@viewer_required
def get_personnel(personnel_id):
    """Récupérer un personnel spécifique"""
    try:
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Personnel non trouvé"}), 404
        
        personnel["_id"] = str(personnel["_id"])
        return jsonify(personnel), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["PUT"])
@admin_required
def update_personnel(personnel_id):
    """Modifier un personnel (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que le personnel existe
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Personnel non trouvé"}), 404
        
        # Préparer les données à mettre à jour
        update_data = {}
        
        if "nom_prenom" in data:
            if not validate_nom_prenom(data["nom_prenom"]):
                return jsonify({"message": "Nom et prénom invalides"}), 400
            update_data["nom_prenom"] = data["nom_prenom"]
        
        if "telephone" in data:
            if not validate_telephone(data["telephone"]):
                return jsonify({"message": "Format de téléphone invalide"}), 400
            update_data["telephone"] = data["telephone"]
        
        if "whatsapp" in data:
            if not validate_whatsapp(data["whatsapp"]):
                return jsonify({"message": "Format de WhatsApp invalide"}), 400
            update_data["whatsapp"] = data["whatsapp"]
        
        if "email" in data:
            if not validate_email(data["email"]):
                return jsonify({"message": "Format d'email invalide"}), 400
            # Vérifier que l'email n'est pas déjà utilisé par un autre personnel
            existing_personnel = personnels_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(personnel_id)}})
            if existing_personnel:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        
        if "adresse" in data:
            if not validate_adresse(data["adresse"]):
                return jsonify({"message": "Format d'adresse invalide"}), 400
            update_data["adresse"] = data["adresse"]
        
        if "note_commentaire" in data:
            if not validate_note_commentaire(data["note_commentaire"]):
                return jsonify({"message": "Format de note/commentaire invalide"}), 400
            update_data["note_commentaire"] = data["note_commentaire"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour le personnel
        result = personnels_col.update_one(
            {"_id": ObjectId(personnel_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Personnel mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["DELETE"])
@admin_required
def delete_personnel(personnel_id):
    """Supprimer un personnel (admin uniquement)"""
    try:
        result = personnels_col.delete_one({"_id": ObjectId(personnel_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Personnel supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Personnel non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression du personnel: {str(e)}"}), 500

# ===========================================
# ROUTES DE DEBUG POUR RAILWAY
# ===========================================

@app.route("/api/debug", methods=["GET"])
def debug_info():
    """Route de diagnostic pour Railway"""
    try:
        # Test de connexion MongoDB
        client.admin.command('ping')
        mongo_status = "Connected"
    except Exception as e:
        mongo_status = f"Error: {str(e)}"
    
    try:
        # Compter les utilisateurs
        user_count = users_col.count_documents({})
        users_status = f"Found {user_count} users"
    except Exception as e:
        users_status = f"Error: {str(e)}"
    
    try:
        # Compter les sources
        sources_count = sources_col.count_documents({})
        sources_status = f"Found {sources_count} sources"
    except Exception as e:
        sources_status = f"Error: {str(e)}"
    
    return jsonify({
        "status": "Debug Info",
        "mongo_uri": MONGO_URI[:50] + "..." if len(MONGO_URI) > 50 else MONGO_URI,
        "mongo_status": mongo_status,
        "users_status": users_status,
        "sources_status": sources_status,
        "jwt_secret_set": bool(app.config["SECRET_KEY"]),
        "environment": {
            "PORT": os.getenv("PORT", "Not set"),
            "JWT_SECRET": "Set" if os.getenv("JWT_SECRET") else "Not set",
            "MONGO_URI": "Set" if os.getenv("MONGO_URI") else "Not set"
        }
    })

# ===========================================
# GESTION DES OFFRES
# ===========================================

@app.route("/api/offres", methods=["GET"])
@viewer_required
def get_offres():
    """Récupérer toutes les offres (admin voit tout, utilisateur voit ses offres)"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {}
        # Tous les utilisateurs (user, admin, spectateur) voient toutes les offres
        # Pas de filtrage par responsable_id
        
        offres = list(offres_col.find(query).sort("updated_at", -1))
        
        for offre in offres:
            offre["_id"] = str(offre["_id"])
            if "responsable_id" in offre:
                offre["responsable_id"] = str(offre["responsable_id"])
                # Ajouter un champ pour indiquer si l'offre appartient à l'utilisateur connecté
                offre["est_mienne"] = (str(offre["responsable_id"]) == str(user_id)) if user_id else False
            else:
                offre["est_mienne"] = False
            # Convertir les dates
            if "date_limite" in offre and offre["date_limite"]:
                if hasattr(offre["date_limite"], 'isoformat'):
                    offre["date_limite"] = offre["date_limite"].isoformat()
            if "created_at" in offre and offre["created_at"]:
                if hasattr(offre["created_at"], 'isoformat'):
                    offre["created_at"] = offre["created_at"].isoformat()
            if "updated_at" in offre and offre["updated_at"]:
                if hasattr(offre["updated_at"], 'isoformat'):
                    offre["updated_at"] = offre["updated_at"].isoformat()
        
        return jsonify(offres), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des offres: {str(e)}")
        return jsonify([]), 200

@app.route("/api/offres", methods=["POST"])
@viewer_required
def add_offre():
    """Ajouter une offre"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        if not user_id:
            return jsonify({"message": "Utilisateur non identifié"}), 401
        
        # Vérifier les permissions de création
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas créer d'offres"}), 403
        
        # Champs requis
        required_fields = ["intitulee", "lien", "client", "date_limite"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not validate_offre_intitulee(data["intitulee"]):
            return jsonify({"message": "Intitulé invalide"}), 400
        
        if not validate_offre_lien(data["lien"]):
            return jsonify({"message": "Lien invalide"}), 400
        
        if not validate_offre_client(data["client"]):
            return jsonify({"message": "Client invalide"}), 400
        
        if not validate_offre_date_limite(data["date_limite"]):
            return jsonify({"message": "Date limite invalide"}), 400
        
        # Validations optionnelles
        if "statut" in data and not validate_offre_statut(data["statut"]):
            return jsonify({"message": "Statut invalide. Doit être: Non préparé, En préparation, ou Envoyée"}), 400
        
        if "documents" in data and not validate_offre_documents(data["documents"]):
            return jsonify({"message": "Format des documents invalide"}), 400
        
        if "note_commentaire" in data and not validate_note_commentaire(data["note_commentaire"]):
            return jsonify({"message": "Format de la note/commentaire invalide"}), 400
        
        # Créer l'offre
        from datetime import datetime
        offre = {
            "intitulee": data["intitulee"],
            "lien": data["lien"],
            "client": data["client"],
            "date_limite": datetime.fromisoformat(data["date_limite"].replace('Z', '+00:00')),
            "statut": data.get("statut", "Non préparé"),
            "responsable_id": ObjectId(user_id),
            "note_commentaire": data.get("note_commentaire", ""),
            "documents": data.get("documents", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = offres_col.insert_one(offre)
        offre["_id"] = str(result.inserted_id)
        offre["responsable_id"] = str(offre["responsable_id"])
        
        return jsonify({"message": "Offre créée avec succès", "offre": offre}), 201
        
    except Exception as e:
        print(f"ERROR: Erreur lors de la création de l'offre: {str(e)}")
        return jsonify({"message": f"Erreur lors de la création de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["GET"])
@viewer_required
def get_offre(offre_id):
    """Récupérer une offre spécifique"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {"_id": ObjectId(offre_id)}
        # Tous les utilisateurs peuvent voir toutes les offres
        # Pas de filtrage par responsable_id
        
        offre = offres_col.find_one(query)
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 404
        
        offre["_id"] = str(offre["_id"])
        if "responsable_id" in offre:
            offre["responsable_id"] = str(offre["responsable_id"])
            # Ajouter un champ pour indiquer si l'offre appartient à l'utilisateur connecté
            offre["est_mienne"] = (str(offre["responsable_id"]) == str(user_id)) if user_id else False
        else:
            offre["est_mienne"] = False
        
        return jsonify(offre), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["PUT"])
@viewer_required
def update_offre(offre_id):
    """Modifier une offre"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Vérifier les permissions de modification
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas modifier les offres"}), 403
        
        # Construire la requête pour vérifier l'existence
        query = {"_id": ObjectId(offre_id)}
        
        offre = offres_col.find_one(query)
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 404
        
        # Vérifier les permissions selon le rôle
        if user_role == "user":
            # L'utilisateur normal ne peut modifier que ses propres offres
            if str(offre.get("responsable_id")) != str(user_id):
                return jsonify({"message": "Accès refusé - Vous ne pouvez modifier que vos propres offres"}), 403
        
        # Préparer les données à mettre à jour
        update_data = {}
        
        if "intitulee" in data:
            if not validate_offre_intitulee(data["intitulee"]):
                return jsonify({"message": "Intitulé invalide"}), 400
            update_data["intitulee"] = data["intitulee"]
        
        if "lien" in data:
            if not validate_offre_lien(data["lien"]):
                return jsonify({"message": "Lien invalide"}), 400
            update_data["lien"] = data["lien"]
        
        if "client" in data:
            if not validate_offre_client(data["client"]):
                return jsonify({"message": "Client invalide"}), 400
            update_data["client"] = data["client"]
        
        if "date_limite" in data:
            if not validate_offre_date_limite(data["date_limite"]):
                return jsonify({"message": "Date limite invalide"}), 400
            update_data["date_limite"] = datetime.fromisoformat(data["date_limite"].replace('Z', '+00:00'))
        
        if "statut" in data:
            if not validate_offre_statut(data["statut"]):
                return jsonify({"message": "Statut invalide. Doit être: Non préparé, En préparation, ou Envoyée"}), 400
            update_data["statut"] = data["statut"]
        
        if "note_commentaire" in data:
            if not validate_note_commentaire(data["note_commentaire"]):
                return jsonify({"message": "Format de la note/commentaire invalide"}), 400
            update_data["note_commentaire"] = data["note_commentaire"]
        
        if "documents" in data:
            if not validate_offre_documents(data["documents"]):
                return jsonify({"message": "Format des documents invalide"}), 400
            update_data["documents"] = data["documents"]
        
        # Gestion du responsable_id (seul l'admin peut réassigner)
        if "responsable_id" in data:
            if user_role != "admin":
                return jsonify({"message": "Accès refusé - Seul l'admin peut réassigner les offres"}), 403
            if not validate_offre_responsable_id(data["responsable_id"]):
                return jsonify({"message": "ID responsable invalide"}), 400
            update_data["responsable_id"] = ObjectId(data["responsable_id"])
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour l'offre
        result = offres_col.update_one(
            {"_id": ObjectId(offre_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Offre mise à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["DELETE"])
@viewer_required
def delete_offre(offre_id):
    """Supprimer une offre"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Vérifier les permissions de suppression
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas supprimer les offres"}), 403
        
        # Construire la requête pour vérifier l'existence
        query = {"_id": ObjectId(offre_id)}
        
        # Vérifier l'existence de l'offre et les permissions
        offre = offres_col.find_one(query)
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 404
        
        # Vérifier les permissions selon le rôle
        if user_role == "user":
            # L'utilisateur normal ne peut supprimer que ses propres offres
            if str(offre.get("responsable_id")) != str(user_id):
                return jsonify({"message": "Accès refusé - Vous ne pouvez supprimer que vos propres offres"}), 403
        
        result = offres_col.delete_one(query)
        
        if result.deleted_count > 0:
            return jsonify({"message": "Offre supprimée avec succès"}), 200
        else:
            return jsonify({"message": "Offre non trouvée ou accès refusé"}), 404
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression de l'offre: {str(e)}"}), 500

@app.route("/api/offres/stats", methods=["GET"])
@viewer_required
def get_offres_stats():
    """Statistiques des offres"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {}
        # Tous les utilisateurs voient les statistiques globales
        # Pas de filtrage par responsable_id
        
        # Compter par statut
        stats = {
            "total_offres": offres_col.count_documents(query),
            "non_prepare_offres": offres_col.count_documents({**query, "statut": "Non préparé"}),
            "en_preparation_offres": offres_col.count_documents({**query, "statut": "En préparation"}),
            "envoyee_offres": offres_col.count_documents({**query, "statut": "Envoyée"})
        }
        
        return jsonify(stats), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des statistiques: {str(e)}")
        return jsonify({
            "total_offres": 0,
            "non_prepare_offres": 0,
            "en_preparation_offres": 0,
            "envoyee_offres": 0
        }), 200

@app.route("/api/test-offres", methods=["GET"])
def test_offres_connection():
    """Test de connexion à la collection offres"""
    try:
        # Test de connexion
        client.admin.command('ping')
        
        # Compter les éléments
        count = offres_col.count_documents({})
        
        return jsonify({
            "status": "Offres OK",
            "message": f"Connexion à la collection offres réussie. {count} offres trouvées.",
            "count": count
        }), 200
    except Exception as e:
        return jsonify({
            "status": "Offres Error",
            "message": f"Erreur de connexion à la collection offres: {str(e)}"
        }), 500
        
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