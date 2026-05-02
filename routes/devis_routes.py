"""Routes pour la gestion des devis"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import devis_col, factures_col, offres_col, clients_col
from auth.decorators import token_required, permission_required
from utils.validators import validate_documents_array
from utils.error_handler import handle_server_error

devis_bp = Blueprint('devis', __name__)


@devis_bp.route("/api/devis", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_devis(current_user_id):
    """Récupérer tous les devis (admin voit tout, utilisateur voit ses devis)"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {}
        if user_role == "user":
            # L'utilisateur ne voit que ses propres devis
            query["responsable_id"] = ObjectId(user_id)
        
        devis = list(devis_col.find(query).sort("created_at", -1))
        
        for devis_item in devis:
            devis_item["_id"] = str(devis_item["_id"])
            if "responsable_id" in devis_item:
                devis_item["responsable_id"] = str(devis_item["responsable_id"])
            if "offre_id" in devis_item:
                devis_item["offre_id"] = str(devis_item["offre_id"])
            if "client_id" in devis_item:
                devis_item["client_id"] = str(devis_item["client_id"])
            # Convertir les dates
            if "date_emission" in devis_item and devis_item["date_emission"]:
                if hasattr(devis_item["date_emission"], 'isoformat'):
                    devis_item["date_emission"] = devis_item["date_emission"].isoformat()
            if "created_at" in devis_item and devis_item["created_at"]:
                if hasattr(devis_item["created_at"], 'isoformat'):
                    devis_item["created_at"] = devis_item["created_at"].isoformat()
            if "updated_at" in devis_item and devis_item["updated_at"]:
                if hasattr(devis_item["updated_at"], 'isoformat'):
                    devis_item["updated_at"] = devis_item["updated_at"].isoformat()
            # S'assurer que les documents sont bien des arrays
            if "document" in devis_item:
                if isinstance(devis_item["document"], str):
                    # Si c'est encore une string (ancien format), convertir en array
                    devis_item["document"] = [devis_item["document"]] if devis_item["document"] else []
                elif not isinstance(devis_item["document"], list):
                    devis_item["document"] = []
        
        return jsonify(devis), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des devis")
        return jsonify([]), 200


@devis_bp.route("/api/devis", methods=["POST"])
@token_required
@permission_required('devis_create')
def create_devis(current_user_id):
    """Créer un nouveau devis"""
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
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas créer de devis"}), 403
        
        # Champs requis
        required_fields = ["numero_devis", "intitule", "date_emission", "offre_id", "client_id", "etat"]
        for field in required_fields:
            if not data.get(field):
                return jsonify({"message": f"Le champ {field} est requis"}), 400
        
        # Validations
        if not data["numero_devis"] or not isinstance(data["numero_devis"], str) or len(data["numero_devis"].strip()) == 0:
            return jsonify({"message": "Numéro de devis invalide"}), 400
   
        if not data["intitule"] or not isinstance(data["intitule"], str) or len(data["intitule"].strip()) == 0:
            return jsonify({"message": "Intitulé invalide"}), 400
        
        # Vérifier la date d'émission
        try:
            datetime.fromisoformat(data["date_emission"].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return jsonify({"message": "Date d'émission invalide"}), 400
        
        # Vérifier que l'offre existe et récupérer ses données
        offre = offres_col.find_one({"_id": ObjectId(data["offre_id"])})
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 400
        
        # Vérifier que le client existe et récupérer ses données
        client = clients_col.find_one({"_id": ObjectId(data["client_id"])})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 400
        
        numero_devis = data["numero_devis"]
        
        # Validation du document (array d'URLs)
        document = data.get("document", [])
        if not validate_documents_array(document):
            return jsonify({"message": "Format des documents invalide (doit être un array d'URLs)"}), 400

        # Créer le devis
        devis = {
            "numero_devis": numero_devis,
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
        
        result = devis_col.insert_one(devis)
        devis["_id"] = str(result.inserted_id)
        devis["responsable_id"] = str(devis["responsable_id"])
        devis["offre_id"] = str(devis["offre_id"])
        devis["client_id"] = str(devis["client_id"])
        
        return jsonify({"message": "Devis créé avec succès", "devis": devis}), 201
        
    except Exception as e:
        message, status = handle_server_error(e, "création du devis")
        return jsonify(message), status


@devis_bp.route("/api/devis/<devis_id>", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_devis_by_id(current_user_id, devis_id):
    """Récupérer un devis spécifique"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Construire la requête
        query = {"_id": ObjectId(devis_id)}
        if user_role == "user":
            # L'utilisateur ne peut voir que ses propres devis
            query["responsable_id"] = ObjectId(user_id)
        
        devis = devis_col.find_one(query)
        if not devis:
            return jsonify({"message": "Devis non trouvé"}), 404
        
        devis["_id"] = str(devis["_id"])
        if "responsable_id" in devis:
            devis["responsable_id"] = str(devis["responsable_id"])
        if "offre_id" in devis:
            devis["offre_id"] = str(devis["offre_id"])
        if "client_id" in devis:
            devis["client_id"] = str(devis["client_id"])
        # S'assurer que les documents sont bien des arrays
        if "document" in devis:
            if isinstance(devis["document"], str):
                # Si c'est encore une string (ancien format), convertir en array
                devis["document"] = [devis["document"]] if devis["document"] else []
            elif not isinstance(devis["document"], list):
                devis["document"] = []
        
        return jsonify(devis), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération du devis")
        return jsonify(message), status


@devis_bp.route("/api/devis/<devis_id>", methods=["PUT"])
@token_required
@permission_required('devis_edit')
def update_devis(current_user_id, devis_id):
    """Modifier un devis"""
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
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas modifier les devis"}), 403
        
        # Construire la requête pour vérifier l'existence
        query = {"_id": ObjectId(devis_id)}
        if user_role == "user":
            # L'utilisateur ne peut modifier que ses propres devis
            query["responsable_id"] = ObjectId(user_id)
        
        devis = devis_col.find_one(query)
        if not devis:
            return jsonify({"message": "Devis non trouvé"}), 404
        
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
            update_data["etat"] = data["etat"]
        
        if "document" in data:
            if not validate_documents_array(data["document"]):
                return jsonify({"message": "Format des documents invalide (doit être un array d'URLs)"}), 400
            update_data["document"] = data["document"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour le devis
        result = devis_col.update_one(
            {"_id": ObjectId(devis_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Devis mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
             
    except Exception as e:
        message, status = handle_server_error(e, "mise à jour du devis")
        return jsonify(message), status


@devis_bp.route("/api/devis/<devis_id>", methods=["DELETE"])
@token_required
@permission_required('devis_delete')
def delete_devis(current_user_id, devis_id):
    """Supprimer un devis"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        # Vérifier les permissions de suppression
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas supprimer les devis"}), 403
        
        # Construire la requête
        query = {"_id": ObjectId(devis_id)}
        if user_role == "user":
            # L'utilisateur ne peut supprimer que ses propres devis
            query["responsable_id"] = ObjectId(user_id)
        
        result = devis_col.delete_one(query)
        
        if result.deleted_count > 0:
            return jsonify({"message": "Devis supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Devis non trouvé"}), 404
             
    except Exception as e:
        message, status = handle_server_error(e, "suppression du devis")
        return jsonify(message), status


@devis_bp.route("/api/devis/etats", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_devis_etats(current_user_id):
    """Récupérer les états possibles pour les devis"""
    return jsonify(["Validé", "Transformé en facture"]), 200


@devis_bp.route("/api/devis/<devis_id>/transform-to-facture", methods=["POST"])
@token_required
@permission_required('devis_edit')
def transform_devis_to_facture(current_user_id, devis_id):
    """Transformer un devis en facture"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
        if not user_id:
            return jsonify({"message": "Utilisateur non identifié"}), 401
        
        # Vérifier les permissions
        if user_role == "spectateur":
            return jsonify({"message": "Accès refusé - Les spectateurs ne peuvent pas transformer les devis"}), 403
        
        # Construire la requête
        query = {"_id": ObjectId(devis_id)}
        if user_role == "user":
            query["responsable_id"] = ObjectId(user_id)
        
        # Récupérer le devis
        devis = devis_col.find_one(query)
        if not devis:
            return jsonify({"message": "Devis non trouvé"}), 404
        
        # Vérifier que le devis est validé
        if devis.get("etat") != "Validé":
            return jsonify({"message": "Seuls les devis validés peuvent être transformés en facture"}), 400
        
        # Récupérer les données du client et de l'offre pour le nom
        client = clients_col.find_one({"_id": devis["client_id"]})
        offre = offres_col.find_one({"_id": devis["offre_id"]})
        nom_client = client.get("nom", "Client").replace(" ", "_") if client else "Client"
        nom_offre = offre.get("titre", "Offre").replace(" ", "_") if offre else "Offre"
        
        # Créer la facture à partir du devis
        facture = {
            "numero_facture": f"Fac_{nom_client}_{nom_offre}",
            "intitule": devis["intitule"],
            "responsable_id": devis["responsable_id"],
            "date_emission": devis["date_emission"],
            "offre_id": devis["offre_id"],
            "client_id": devis["client_id"],
            "etat": "A envoyer au client",
            "document": devis.get("document", []),
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insérer la facture
        result = factures_col.insert_one(facture)
        facture["_id"] = str(result.inserted_id)
        facture["responsable_id"] = str(facture["responsable_id"])
        facture["offre_id"] = str(facture["offre_id"])
        facture["client_id"] = str(facture["client_id"])
        
        # Mettre à jour le statut du devis
        devis_col.update_one(
            {"_id": ObjectId(devis_id)},
            {"$set": {"etat": "Transformé en facture", "updated_at": datetime.utcnow()}}
        )
        
        return jsonify({"message": "Devis transformé en facture avec succès", "facture": facture}), 201
         
    except Exception as e:
        message, status = handle_server_error(e, "transformation du devis")
        return jsonify(message), status












