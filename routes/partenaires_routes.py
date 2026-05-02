"""Routes pour la gestion des partenaires"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import partenaires_col
from utils.error_handler import handle_server_error
from auth.decorators import token_required, permission_required
from utils.validators import (
    validate_raison_sociale, validate_nom_prenom, validate_telephone,
    validate_email, validate_whatsapp, validate_adresse, validate_note_commentaire
)

partenaires_bp = Blueprint('partenaires', __name__)


@partenaires_bp.route("/api/partenaires", methods=["GET"])
@token_required
@permission_required('partners_view')
def get_partenaires(current_user_id):
    """Récupérer tous les partenaires"""
    try:
        partenaires = list(partenaires_col.find().sort("raison_sociale", 1))
        
        for partenaire in partenaires:
            partenaire["_id"] = str(partenaire["_id"])
        
        return jsonify(partenaires), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des partenaires")
        return jsonify([]), 200


@partenaires_bp.route("/api/partenaires", methods=["POST"])
@token_required
@permission_required('partners_manage')
def create_partenaire(current_user_id):
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
        message, status = handle_server_error(e, "création du partenaire")
        return jsonify(message), status


@partenaires_bp.route("/api/partenaires/<partenaire_id>", methods=["GET"])
@token_required
@permission_required('partners_view')
def get_partenaire(current_user_id, partenaire_id):
    """Récupérer un partenaire spécifique"""
    try:
        partenaire = partenaires_col.find_one({"_id": ObjectId(partenaire_id)})
        if not partenaire:
            return jsonify({"message": "Partenaire non trouvé"}), 404
        
        partenaire["_id"] = str(partenaire["_id"])
        return jsonify(partenaire), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération du partenaire")
        return jsonify(message), status


@partenaires_bp.route("/api/partenaires/<partenaire_id>", methods=["PUT"])
@token_required
@permission_required('partners_manage')
def update_partenaire(current_user_id, partenaire_id):
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
        message, status = handle_server_error(e, "mise à jour du partenaire")
        return jsonify(message), status


@partenaires_bp.route("/api/partenaires/<partenaire_id>", methods=["DELETE"])
@token_required
@permission_required('partners_manage')
def delete_partenaire(current_user_id, partenaire_id):
    """Supprimer un partenaire (admin uniquement)"""
    try:
        result = partenaires_col.delete_one({"_id": ObjectId(partenaire_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Partenaire supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Partenaire non trouvé"}), 404
            
    except Exception as e:
        message, status = handle_server_error(e, "suppression du partenaire")
        return jsonify(message), status
