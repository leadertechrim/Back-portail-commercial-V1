"""Routes pour la gestion des utilisateurs"""
from flask import Blueprint, request, jsonify, current_app
from flask_bcrypt import Bcrypt
import jwt
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from database import users_col, roles_collection
from auth.decorators import token_required, permission_required, admin_required
from utils.validators import (
    validate_email, validate_password, validate_telephone, validate_whatsapp,
    validate_adresse, validate_statut, validate_user_fonction
)
from crypto_utils import encrypt_password, decrypt_password
from utils.error_handler import handle_server_error

users_bp = Blueprint('users', __name__)


def optional_auth(f):
    """Décorateur pour authentification optionnelle (pour Railway)"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if auth:
            try:
                token = auth.split(" ")[1]
                decoded = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
                request.current_user = decoded
            except:
                request.current_user = None
        else:
            request.current_user = None
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function


@users_bp.route("/api/users", methods=["GET"])
@token_required
def get_users(current_user_id):
    """Récupérer tous les utilisateurs"""
    try:
        # Vérifier les permissions - soit users_manage, soit cart_view_all
        user_permissions = request.current_user.get('permissions', []) if hasattr(request, 'current_user') else []
        user_role = request.current_user.get('role', '') if hasattr(request, 'current_user') else ''
        
        # Rôles privilégiés automatiquement autorisés
        privileged_roles = ["admin", "supadmin", "administrateur principal", "administrateur système"]
        # Rôles autorisés à voir les utilisateurs (lecture seule)
        allowed_view_roles = ["admin", "supadmin", "administrateur principal", "administrateur système", "commercial"]
        is_privileged = user_role.lower() in privileged_roles
        can_view_users = user_role.lower() in [r.lower() for r in allowed_view_roles]
        
        has_permission = (
            is_privileged or 
            can_view_users or
            'users_manage' in user_permissions or 
            'cart_view_all' in user_permissions
        )
        
        if not has_permission:
            return jsonify({
                "message": "Permission 'users_manage' ou 'cart_view_all' requise"
            }), 403
        
        # Vérifier la connexion à la base de données
        from database import client
        client.admin.command('ping')
        
        # Récupérer les utilisateurs
        users = list(users_col.find({}, {"password": 0}).sort("email", 1))
        
        # Convertir les ObjectId en string
        for user in users:
            user["_id"] = str(user["_id"])
        
        return jsonify(users), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des utilisateurs")
        return jsonify(message), status


@users_bp.route("/api/users", methods=["POST"])
@token_required
@permission_required('users_manage')
def create_user(current_user_id):
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
    
    # Valider le rôle - accepter tous les rôles existants dans la base
    existing_role = roles_collection.find_one({'nom': data["role"]})
    if not existing_role:
        return jsonify({"message": f"Rôle '{data['role']}' n'existe pas dans la base de données"}), 400
    
    # Validations des nouveaux champs
    telephone = data.get("telephone", "")
    whatsapp = data.get("whatsapp", "")
    adresse = data.get("adresse", "")
    statut = data.get("statut", "actif")
    fonction = data.get("Fonction", "")
    # Validation des champs
    if not validate_telephone(telephone):
        return jsonify({"message": "Format de téléphone invalide"}), 400
    if not validate_whatsapp(whatsapp):
        return jsonify({"message": "Format de WhatsApp invalide"}), 400
    if not validate_adresse(adresse):
        return jsonify({"message": "Format d'adresse invalide"}), 400
    if not validate_statut(statut):
        return jsonify({"message": "Statut invalide"}), 400
    
    try:
        bcrypt = current_app.bcrypt
        # Hasher ET chiffrer le mot de passe
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        encrypted_password = encrypt_password(data["password"])  # 🆕 Chiffrement AES
        
        # Créer l'utilisateur
        user = {
            "name": data["name"],
            "email": data["email"],
            "password": hashed_password,
            "password_encrypted": encrypted_password,  # 🆕 Mot de passe chiffré (réversible)
            "role": data["role"],
            "telephone": telephone,
            "whatsapp": whatsapp,
            "adresse": adresse,
            "statut": statut,
            "Fonction": fonction,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = users_col.insert_one(user)
        
        user["_id"] = str(result.inserted_id)
        del user["password"]  # Ne pas retourner le mot de passe
        
        return jsonify({"message": "Utilisateur créé avec succès", "user": user}), 201
    except Exception as e:
        return jsonify({"message": "Erreur lors de la création de l'utilisateur"}), 500


@users_bp.route("/api/users/<user_id>", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_user(current_user_id, user_id):
    """Récupérer un utilisateur spécifique (admin uniquement)"""
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)}, {"password": 0})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        user["_id"] = str(user["_id"])
        return jsonify(user), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération de l'utilisateur")
        return jsonify(message), status


@users_bp.route("/api/users/<user_id>/decrypt-password", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_user_decrypted_password(current_user_id, user_id):
    """
    Déchiffrer le mot de passe d'un utilisateur (admin uniquement)
    ⚠️ ATTENTION : Ceci est une faille de sécurité volontaire
    """
    try:
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        encrypted_password = user.get("password_encrypted", "")
        
        if not encrypted_password:
            return jsonify({
                "message": "Mot de passe non disponible",
                "password": "",
                "note": "L'utilisateur a été créé avant la mise en place du chiffrement"
            }), 200
        
        # Déchiffrer le mot de passe
        decrypted_password = decrypt_password(encrypted_password)
        
        return jsonify({
            "message": "Mot de passe déchiffré avec succès",
            "password": decrypted_password,
            "user_id": str(user["_id"]),
            "user_email": user.get("email", "")
        }), 200
        
    except Exception as e:
        message, status = handle_server_error(e, "déchiffrement du mot de passe")
        return jsonify({
            "message": message.get("message", "Erreur lors du déchiffrement"),
            "password": ""
        }), status


@users_bp.route("/api/users/<user_id>", methods=["PUT"])
@token_required
@permission_required('users_manage')
def update_user(current_user_id, user_id):
    """Modifier un utilisateur (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que l'utilisateur existe
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        bcrypt = current_app.bcrypt
        
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
            # Valider le rôle - accepter tous les rôles existants dans la base
            existing_role = roles_collection.find_one({'nom': data["role"]})
            if not existing_role:
                return jsonify({"message": f"Rôle '{data['role']}' n'existe pas dans la base de données"}), 400
            update_data["role"] = data["role"]
        if "password" in data and data["password"]:
            if not validate_password(data["password"]):
                return jsonify({"message": "Mot de passe doit contenir au moins 6 caractères"}), 400
            # Hacher ET chiffrer le nouveau mot de passe
            hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
            encrypted_password = encrypt_password(data["password"])  # 🆕 Chiffrement AES
            update_data["password"] = hashed_password
            update_data["password_encrypted"] = encrypted_password  # 🆕
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
        if "Fonction" in data:
            update_data["Fonction"] = data["Fonction"]
        
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
        message, status = handle_server_error(e, "mise à jour de l'utilisateur")
        return jsonify(message), status


@users_bp.route("/api/users/<user_id>", methods=["DELETE"])
@token_required
@permission_required('users_manage')
def delete_user(current_user_id, user_id):
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
        message, status = handle_server_error(e, "suppression de l'utilisateur")
        return jsonify(message), status


@users_bp.route("/api/users/stats", methods=["GET"])
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
        message, status = handle_server_error(e, "récupération des statistiques")
        return jsonify(message), status


@users_bp.route("/api/users/<user_id>/change-password", methods=["POST"])
@token_required
@permission_required('users_manage')
def change_user_password(current_user_id, user_id):
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
        bcrypt = current_app.bcrypt
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


@users_bp.route("/api/admin/change-password", methods=["POST"])
@admin_required
def admin_change_own_password(current_user_id):
    """Changer son propre mot de passe (admin uniquement)"""
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
        bcrypt = current_app.bcrypt
        # Récupérer l'utilisateur admin
        user = users_col.find_one({"_id": ObjectId(current_user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier le mot de passe actuel
        if not bcrypt.check_password_hash(user["password"], data["current_password"]):
            return jsonify({"message": "Mot de passe actuel incorrect"}), 400
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["new_password"]).decode("utf-8")
        
        # Mettre à jour le mot de passe
        users_col.update_one(
            {"_id": ObjectId(current_user_id)},
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


@users_bp.route("/api/test-jwt", methods=["GET"])
def test_jwt():
    """Test de la configuration JWT"""
    try:
        # Test de génération de token
        test_token = jwt.encode({
            "test": "value",
            "exp": datetime.utcnow() + timedelta(minutes=1)
        }, current_app.config["SECRET_KEY"], algorithm="HS256")
        
        # Test de décodage
        decoded = jwt.decode(test_token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        
        return jsonify({
            "status": "JWT OK",
            "secret_key_set": bool(current_app.config["SECRET_KEY"]),
            "test_decoded": decoded
        })
    except Exception as e:
        message, status = handle_server_error(e, "test JWT")
        return jsonify(message), status

