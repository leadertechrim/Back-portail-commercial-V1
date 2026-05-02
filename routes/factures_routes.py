"""Routes pour la gestion des factures"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import factures_col, offres_col, clients_col
from auth.decorators import token_required, permission_required
from utils.validators import validate_documents_array
from utils.error_handler import handle_server_error

factures_bp = Blueprint('factures', __name__)


@factures_bp.route("/api/factures", methods=["GET"])
@token_required
@permission_required('factures_view')
def get_factures(current_user_id):
    """Récupérer toutes les factures (admin voit tout, utilisateur voit ses factures)"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {}
        if user_role == "user":
            # L'utilisateur ne voit que ses propres factures
            query["responsable_id"] = ObjectId(user_id)
        
        factures = list(factures_col.find(query).sort("created_at", -1))
        
        for facture in factures:
            facture["_id"] = str(facture["_id"])
            if "responsable_id" in facture:
                facture["responsable_id"] = str(facture["responsable_id"])
            if "offre_id" in facture:
                facture["offre_id"] = str(facture["offre_id"])
            if "client_id" in facture:
                facture["client_id"] = str(facture["client_id"])
            # Convertir les dates
            if "date_emission" in facture and facture["date_emission"]:
                if hasattr(facture["date_emission"], 'isoformat'):
                    facture["date_emission"] = facture["date_emission"].isoformat()
            if "created_at" in facture and facture["created_at"]:
                if hasattr(facture["created_at"], 'isoformat'):
                    facture["created_at"] = facture["created_at"].isoformat()
            if "updated_at" in facture and facture["updated_at"]:
                if hasattr(facture["updated_at"], 'isoformat'):
                    facture["updated_at"] = facture["updated_at"].isoformat()
            # S'assurer que les documents sont bien des arrays
            if "document" in facture:
                if isinstance(facture["document"], str):
                    # Si c'est encore une string (ancien format), convertir en array
                    facture["document"] = [facture["document"]] if facture["document"] else []
                elif not isinstance(facture["document"], list):
                    facture["document"] = []
        
        return jsonify(factures), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des factures")
        return jsonify([]), 200


@factures_bp.route("/api/factures", methods=["POST"])
@token_required
@permission_required('factures_create')
def create_facture(current_user_id):
    """Créer une nouvelle facture"""
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
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas créer de factures"}), 403
        
        # Champs requis
        required_fields = ["numero_facture", "intitule", "date_emission", "offre_id", "client_id", "etat"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not data["numero_facture"] or not isinstance(data["numero_facture"], str) or len(data["numero_facture"].strip()) == 0:
            return jsonify({"message": "Numéro de facture invalide"}), 400

        if not data["intitule"] or not isinstance(data["intitule"], str) or len(data["intitule"].strip()) == 0:
            return jsonify({"message": "Intitulé invalide"}), 400
        
        # Vérifier la date d'émission
        try:
            datetime.fromisoformat(data["date_emission"].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return jsonify({"message": "Date d'émission invalide"}), 400
        
        # Nettoyer l'état (supprimer les espaces en début/fin)
        if "etat" in data and data["etat"]:
            data["etat"] = data["etat"].strip()
        
        # Vérifier que l'offre existe et récupérer ses données
        offre = offres_col.find_one({"_id": ObjectId(data["offre_id"])})
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 400
        
        # Vérifier que le client existe et récupérer ses données
        client = clients_col.find_one({"_id": ObjectId(data["client_id"])})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 400
        
        numero_facture = data["numero_facture"]
        # Validation du document (array d'URLs)
        document = data.get("document", [])
        if not validate_documents_array(document):
            return jsonify({"message": "Format des documents invalide (doit être un array d'URLs)"}), 400

        # Créer la facture
        facture = {
            "numero_facture": numero_facture,
            "intitule": data["intitule"],
            "responsable_id": ObjectId(user_id),
            "date_emission": datetime.fromisoformat(data["date_emission"].replace('Z', '+00:00')),
            "offre_id": ObjectId(data["offre_id"]),
            "client_id": ObjectId(data["client_id"]),
            "etat": data["etat"],
            "document": document,  # Array d'URLs
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = factures_col.insert_one(facture)
        facture["_id"] = str(result.inserted_id)
        facture["responsable_id"] = str(facture["responsable_id"])
        facture["offre_id"] = str(facture["offre_id"])
        facture["client_id"] = str(facture["client_id"])
        
        return jsonify({"message": "Facture créée avec succès", "facture": facture}), 201
        
    except Exception as e:
        message, status = handle_server_error(e, "création de la facture")
        return jsonify(message), status


@factures_bp.route("/api/factures/<facture_id>", methods=["GET"])
@token_required
@permission_required('factures_view')
def get_facture_by_id(current_user_id, facture_id):
    """Récupérer une facture spécifique"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {"_id": ObjectId(facture_id)}
        if user_role == "user":
            # L'utilisateur ne peut voir que ses propres factures
            query["responsable_id"] = ObjectId(user_id)
        
        facture = factures_col.find_one(query)
        if not facture:
            return jsonify({"message": "Facture non trouvée"}), 404
        
        facture["_id"] = str(facture["_id"])
        if "responsable_id" in facture:
            facture["responsable_id"] = str(facture["responsable_id"])
        if "offre_id" in facture:
            facture["offre_id"] = str(facture["offre_id"])
        if "client_id" in facture:
            facture["client_id"] = str(facture["client_id"])
        # S'assurer que les documents sont bien des arrays
        if "document" in facture:
            if isinstance(facture["document"], str):
                # Si c'est encore une string (ancien format), convertir en array
                facture["document"] = [facture["document"]] if facture["document"] else []
            elif not isinstance(facture["document"], list):
                facture["document"] = []
        
        return jsonify(facture), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération de la facture")
        return jsonify(message), status


@factures_bp.route("/api/factures/<facture_id>", methods=["PUT"])
@token_required
@permission_required('factures_edit')
def update_facture(current_user_id, facture_id):
    """Modifier une facture"""
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
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas modifier les factures"}), 403
        
        # Construire la requête pour vérifier l'existence
        query = {"_id": ObjectId(facture_id)}
        if user_role == "user":
            # L'utilisateur ne peut modifier que ses propres factures
            query["responsable_id"] = ObjectId(user_id)
        
        facture = factures_col.find_one(query)
        if not facture:
            return jsonify({"message": "Facture non trouvée"}), 404
        
        # Préparer les données à mettre à jour
        update_data = {}
        
        if "intitule" in data:
            if not data["intitule"] or not isinstance(data["intitule"], str) or len(data["intitule"].strip()) == 0:
                return jsonify({"message": "Intitulé invalide"}), 400
            update_data["intitule"] = data["intitule"]
        
        if "date_emission" in data:
            try:
                datetime.fromisoformat(data["date_emission"].replace('Z', '+00:00'))
                update_data["date_emission"] = datetime.fromisoformat(data["date_emission"].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({"message": "Date d'émission invalide"}), 400
        
        if "etat" in data:
            # Nettoyer l'état (supprimer les espaces en début/fin)
            data["etat"] = data["etat"].strip()
            update_data["etat"] = data["etat"]
        
        if "document" in data:
            if not validate_documents_array(data["document"]):
                return jsonify({"message": "Format des documents invalide (doit être un array d'URLs)"}), 400
            update_data["document"] = data["document"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour la facture
        result = factures_col.update_one(
            {"_id": ObjectId(facture_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Facture mise à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
             
    except Exception as e:
        message, status = handle_server_error(e, "mise à jour de la facture")
        return jsonify(message), status


@factures_bp.route("/api/factures/<facture_id>", methods=["DELETE"])
@token_required
@permission_required('factures_delete')
def delete_facture(current_user_id, facture_id):
    """Supprimer une facture"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Vérifier les permissions de suppression
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas supprimer les factures"}), 403
        
        # Construire la requête
        query = {"_id": ObjectId(facture_id)}
        if user_role == "user":
            # L'utilisateur ne peut supprimer que ses propres factures
            query["responsable_id"] = ObjectId(user_id)
        
        result = factures_col.delete_one(query)
        
        if result.deleted_count > 0:
            return jsonify({"message": "Facture supprimée avec succès"}), 200
        else:
            return jsonify({"message": "Facture non trouvée"}), 404
             
    except Exception as e:
        message, status = handle_server_error(e, "suppression de la facture")
        return jsonify(message), status


@factures_bp.route("/api/factures/etats", methods=["GET"])
@token_required
@permission_required('factures_view')
def get_factures_etats(current_user_id):
    """Récupérer les états possibles pour les factures"""
    return jsonify(["A envoyer au client", "En attente de payement", "Payée"]), 200












