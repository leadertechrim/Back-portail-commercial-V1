"""Routes pour la gestion des clients"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import clients_col
from utils.error_handler import handle_server_error
from auth.decorators import token_required, permission_required
from utils.validators import (
    validate_raison_sociale, validate_nom_prenom, validate_telephone,
    validate_email, validate_whatsapp, validate_adresse, validate_note_commentaire
)

clients_bp = Blueprint('clients', __name__)


@clients_bp.route("/api/clients", methods=["GET"])
@token_required
@permission_required('clients_view')
def get_clients(current_user_id):
    """Récupérer tous les clients"""
    try:
        clients = list(clients_col.find().sort("raison_sociale", 1))
        
        for client in clients:
            client["_id"] = str(client["_id"])
        
        return jsonify(clients), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des clients")
        return jsonify([]), 200


@clients_bp.route("/api/clients", methods=["POST"])
@token_required
@permission_required('clients_create')
def create_client(current_user_id):
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
        message, status = handle_server_error(e, "création du client")
        return jsonify(message), status


@clients_bp.route("/api/clients/<client_id>", methods=["GET"])
@token_required
@permission_required('clients_view')
def get_client(current_user_id, client_id):
    """Récupérer un client spécifique"""
    try:
        client = clients_col.find_one({"_id": ObjectId(client_id)})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 404
        
        client["_id"] = str(client["_id"])
        return jsonify(client), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération du client")
        return jsonify(message), status


@clients_bp.route("/api/clients/<client_id>", methods=["PUT"])
@token_required
@permission_required('clients_edit')
def update_client(current_user_id, client_id):
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
        message, status = handle_server_error(e, "mise à jour du client")
        return jsonify(message), status


@clients_bp.route("/api/clients/<client_id>", methods=["DELETE"])
@token_required
@permission_required('clients_delete')
def delete_client(current_user_id, client_id):
    """Supprimer un client (admin uniquement)"""
    try:
        result = clients_col.delete_one({"_id": ObjectId(client_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Client supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Client non trouvé"}), 404
            
    except Exception as e:
        message, status = handle_server_error(e, "suppression du client")
        return jsonify(message), status
