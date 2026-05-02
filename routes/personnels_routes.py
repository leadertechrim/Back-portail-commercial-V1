"""Routes pour la gestion du personnel"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import personnels_col
from utils.error_handler import handle_server_error
from auth.decorators import token_required, permission_required
from utils.validators import (
    validate_nom_prenom, validate_telephone, validate_email,
    validate_whatsapp, validate_adresse, validate_user_fonction
)

personnels_bp = Blueprint('personnels', __name__)


@personnels_bp.route("/api/personnels", methods=["GET"])
@token_required
@permission_required('personnel_view')
def get_personnels(current_user_id):
    """Récupérer tout le personnel"""
    try:
        personnels = list(personnels_col.find().sort("nom_prenom", 1))
        
        for personnel in personnels:
            personnel["_id"] = str(personnel["_id"])
        
        return jsonify(personnels), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération du personnel")
        return jsonify([]), 200


@personnels_bp.route("/api/personnels", methods=["POST"])
@token_required
@permission_required('personnel_create')
def create_personnel(current_user_id):
    """Créer un nouveau membre du personnel (admin uniquement)"""
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
        fonction = data.get("Fonction", "")
        
        if whatsapp and not validate_whatsapp(whatsapp):
            return jsonify({"message": "Format de WhatsApp invalide"}), 400
        if adresse and not validate_adresse(adresse):
            return jsonify({"message": "Format d'adresse invalide"}), 400
        if fonction and not validate_user_fonction(fonction):
            return jsonify({"message": "Format de fonction invalide"}), 400
        
        # Vérifier si l'email existe déjà
        if personnels_col.find_one({"email": data["email"]}):
            return jsonify({"message": "Un membre du personnel avec cet email existe déjà"}), 400
        
        # Créer le membre du personnel
        personnel = {
            "nom_prenom": data["nom_prenom"],
            "telephone": data["telephone"],
            "whatsapp": whatsapp,
            "email": data["email"],
            "adresse": adresse,
            "Fonction": fonction,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = personnels_col.insert_one(personnel)
        personnel["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Membre du personnel créé avec succès", "personnel": personnel}), 201
        
    except Exception as e:
        message, status = handle_server_error(e, "création du membre du personnel")
        return jsonify(message), status


@personnels_bp.route("/api/personnels/<personnel_id>", methods=["GET"])
@token_required
@permission_required('personnel_view')
def get_personnel(current_user_id, personnel_id):
    """Récupérer un membre du personnel spécifique"""
    try:
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Membre du personnel non trouvé"}), 404
        
        personnel["_id"] = str(personnel["_id"])
        return jsonify(personnel), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération du membre du personnel")
        return jsonify(message), status


@personnels_bp.route("/api/personnels/<personnel_id>", methods=["PUT"])
@token_required
@permission_required('personnel_edit')
def update_personnel(current_user_id, personnel_id):
    """Modifier un membre du personnel (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que le membre du personnel existe
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Membre du personnel non trouvé"}), 404
        
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
            # Vérifier que l'email n'est pas déjà utilisé par un autre membre du personnel
            existing_personnel = personnels_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(personnel_id)}})
            if existing_personnel:
                return jsonify({"message": "Cet email est déjà utilisé"}), 400
            update_data["email"] = data["email"]
        
        if "adresse" in data:
            if not validate_adresse(data["adresse"]):
                return jsonify({"message": "Format d'adresse invalide"}), 400
            update_data["adresse"] = data["adresse"]
        
        if "Fonction" in data:
            if not validate_user_fonction(data["Fonction"]):
                return jsonify({"message": "Format de fonction invalide"}), 400
            update_data["Fonction"] = data["Fonction"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour le membre du personnel
        result = personnels_col.update_one(
            {"_id": ObjectId(personnel_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Membre du personnel mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        message, status = handle_server_error(e, "mise à jour du membre du personnel")
        return jsonify(message), status


@personnels_bp.route("/api/personnels/<personnel_id>", methods=["DELETE"])
@token_required
@permission_required('personnel_delete')
def delete_personnel(current_user_id, personnel_id):
    """Supprimer un membre du personnel (admin uniquement)"""
    try:
        result = personnels_col.delete_one({"_id": ObjectId(personnel_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Membre du personnel supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Membre du personnel non trouvé"}), 404
            
    except Exception as e:
        message, status = handle_server_error(e, "suppression du membre du personnel")
        return jsonify(message), status
