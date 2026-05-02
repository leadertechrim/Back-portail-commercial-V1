"""Routes d'authentification"""
from flask import Blueprint, request, jsonify, current_app
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta
from database import users_col, roles_collection
from utils.validators import (
    validate_email, validate_password, validate_telephone, 
    validate_whatsapp, validate_adresse, validate_statut, validate_user_fonction
)
from utils.error_handler import handle_server_error

auth_bp = Blueprint('auth', __name__)

# Note: Les routes frontend (/, /admin, /login GET) sont maintenant gérées par React
# Ce blueprint ne contient que les routes API backend


@auth_bp.route("/register", methods=["POST"])
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
    fonction = data.get("Fonction", "")

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
    if not validate_user_fonction(fonction):
        return jsonify({"message": "Format de fonction invalide"}), 400

    # Valider le rôle - accepter tous les rôles existants dans la base
    existing_role = roles_collection.find_one({'nom': role})
    if not existing_role:
        return jsonify({"message": f"Rôle '{role}' n'existe pas dans la base de données"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"message": "Utilisateur déjà existant"}), 400

    bcrypt = current_app.bcrypt
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
        "Fonction": fonction,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    users_col.insert_one(user)
    return jsonify({"message": "Utilisateur créé"}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        email = data.get("email")
        password = data.get("password")
        
        if not email or not password:
            return jsonify({"message": "Email et mot de passe requis"}), 400
        
        user = users_col.find_one({"email": email})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404

        bcrypt = current_app.bcrypt
        if bcrypt.check_password_hash(user["password"], password):
            token = jwt.encode({
                "user_id": str(user["_id"]),
                "role": user.get("role", "user"),
                "exp": datetime.utcnow() + timedelta(days=7)
            }, current_app.config["SECRET_KEY"], algorithm="HS256")
            
            return jsonify({
                "token": token, 
                "user_id": str(user["_id"]),
                "role": user.get("role", "user"), 
                "name": user.get("name", ""),
                "email": user.get("email", ""),
                "telephone": user.get("telephone", ""),
                "whatsapp": user.get("whatsapp", ""),
                "adresse": user.get("adresse", ""),
                "statut": user.get("statut", "actif"),
                "fonction": user.get("Fonction", "")
            })
        else:
            return jsonify({"message": "Mot de passe incorrect"}), 401
    
    except Exception as e:
        message, status = handle_server_error(e, "authentification")
        return jsonify(message), status

