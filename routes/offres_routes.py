"""Routes pour la gestion des offres"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import client, offres_col
from auth.decorators import token_required, permission_required
from utils.validators import (
    validate_offre_intitulee, validate_offre_lien, validate_offre_client,
    validate_offre_date_limite, validate_offre_responsable_id, validate_offre_categorie,
    validate_offre_numero, validate_offre_partenaire, validate_offre_documents,
    validate_note_commentaire
)
from utils.error_handler import handle_server_error

offres_bp = Blueprint('offres', __name__)


@offres_bp.route("/api/offres", methods=["GET"])
@token_required
def get_offres(current_user_id):
    """Récupérer toutes les offres (admin voit tout, utilisateur voit ses offres)"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user_id or (current_user.get('user_id') if current_user else None)
        user_role = current_user.get('role') if current_user else None
        user_permissions = current_user.get('permissions', []) if current_user else []
        
        # Vérifier les permissions du panier - INDÉPENDANTE des autres permissions
        privileged_roles = ["admin", "supadmin", "administrateur principal", "administrateur système"]
        is_privileged = user_role.lower() in privileged_roles if user_role else False
        
        # La permission cart_view seule suffit pour voir le menu panier
        has_cart_view = is_privileged or 'cart_view' in user_permissions
        has_cart_view_all = is_privileged or 'cart_view_all' in user_permissions
        
        # Si l'utilisateur a cart_view OU cart_view_all, il peut accéder au panier
        if not has_cart_view and not has_cart_view_all:
            return jsonify({
                "message": "Permission 'cart_view' ou 'cart_view_all' requise"
            }), 403
        
        # Construire la requête selon les permissions
        query = {}
        
        # Si l'utilisateur a cart_view_all, il voit toutes les offres
        # Sinon, avec cart_view seul, il voit ses propres offres (ou liste vide si pas d'ID)
        if not has_cart_view_all:
            # Les utilisateurs avec seulement cart_view ne voient que leurs offres
            if user_id:
                query["responsable_id"] = ObjectId(user_id)
            # Si pas d'ID utilisateur mais a cart_view, retourner une liste vide (menu visible mais pas d'offres)
            # C'est normal - le menu panier doit être visible même sans offres
        # Ceux avec cart_view_all voient toutes les offres (pas de filtrage)
        
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
            
            # Mapping des nouveaux champs pour compatibilité
            if "Catégorie" in offre:
                offre["categorie"] = offre["Catégorie"]
            if "N-Offre" in offre:
                offre["numero"] = offre["N-Offre"]
            if "Partenaire" in offre:
                offre["partenaire"] = offre["Partenaire"]
        
        return jsonify(offres), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des offres")
        return jsonify([]), 200


@offres_bp.route("/api/offres", methods=["POST"])
@token_required
@permission_required('cart_add')
def add_offre(current_user_id):
    """Ajouter une offre"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        
        # Utiliser directement current_user_id passé par le décorateur @token_required
        user_id = current_user_id
        
        # Récupérer les infos de l'utilisateur depuis la base pour obtenir son rôle
        current_user = getattr(request, 'current_user', None)
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
        if "documents" in data and not validate_offre_documents(data["documents"]):
            return jsonify({"message": "Format des documents invalide"}), 400
        
        if "note_commentaire" in data and not validate_note_commentaire(data["note_commentaire"]):
            return jsonify({"message": "Format de la note/commentaire invalide"}), 400

        # Validations pour les nouveaux champs
        if "Catégorie" in data and not validate_offre_categorie(data["Catégorie"]):
            return jsonify({"message": "Catégorie invalide. Doit être: national, international"}), 400
        
        if "N-Offre" in data and not validate_offre_numero(data["N-Offre"]):
            return jsonify({"message": "Numéro d'offre invalide"}), 400
        
        if "Partenaire" in data and not validate_offre_partenaire(data["Partenaire"]):
            return jsonify({"message": "Partenaire invalide"}), 400
    
        # Créer l'offre
        offre = {
            "intitulee": data["intitulee"],
            "lien": data["lien"],
            "client": data["client"],
            "date_limite": datetime.fromisoformat(data["date_limite"].replace('Z', '+00:00')),
            "statut": data.get("statut", "Non préparé"),
            "responsable_id": ObjectId(user_id),
            "note_commentaire": data.get("note_commentaire", ""),
            "documents": data.get("documents", []),
            "Catégorie": data.get("Catégorie", ""),  # Nom original
            "N-Offre": data.get("N-Offre", ""),      # Nom original
            "Partenaire": data.get("Partenaire", ""), # Nom original
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = offres_col.insert_one(offre)
        offre["_id"] = str(result.inserted_id)
        offre["responsable_id"] = str(offre["responsable_id"])
        
        return jsonify({"message": "Offre créée avec succès", "offre": offre}), 201
        
    except Exception as e:
        message, status = handle_server_error(e, "création de l'offre")
        return jsonify(message), status


@offres_bp.route("/api/offres/<offre_id>", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_offre(current_user_id, offre_id):
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
        
        # Mapping des nouveaux champs pour compatibilité
        if "Catégorie" in offre:
            offre["categorie"] = offre["Catégorie"]
        if "N-Offre" in offre:
            offre["numero"] = offre["N-Offre"]
        if "Partenaire" in offre:
            offre["partenaire"] = offre["Partenaire"]
        
        return jsonify(offre), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération de l'offre")
        return jsonify(message), status


@offres_bp.route("/api/offres/<offre_id>", methods=["PUT"])
@token_required
@permission_required('devis_edit')
def update_offre(current_user_id, offre_id):
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
            update_data["statut"] = data["statut"]
        
        if "note_commentaire" in data:
            if not validate_note_commentaire(data["note_commentaire"]):
                return jsonify({"message": "Format de la note/commentaire invalide"}), 400
            update_data["note_commentaire"] = data["note_commentaire"]
        
        if "documents" in data:
            if not validate_offre_documents(data["documents"]):
                return jsonify({"message": "Format des documents invalide"}), 400
            update_data["documents"] = data["documents"]
        
        # Gestion des nouveaux champs - toujours mettre à jour même si vides
        if "Catégorie" in data:
            if not validate_offre_categorie(data["Catégorie"]):
                return jsonify({"message": "Catégorie invalide. Doit être: nationale, internationale"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["Catégorie"] = data["Catégorie"]  # Nom original
            update_data["categorie"] = data["Catégorie"]  # Nom mappé
        
        if "N-Offre" in data:
            if not validate_offre_numero(data["N-Offre"]):
                return jsonify({"message": "Numéro d'offre invalide"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["N-Offre"] = data["N-Offre"]  # Nom original
            update_data["numero"] = data["N-Offre"]  # Nom mappé
        
        if "Partenaire" in data:
            if not validate_offre_partenaire(data["Partenaire"]):
                return jsonify({"message": "Partenaire invalide"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["Partenaire"] = data["Partenaire"]  # Nom original
            update_data["partenaire"] = data["Partenaire"]  # Nom mappé
        
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
        message, status = handle_server_error(e, "mise à jour de l'offre")
        return jsonify(message), status


@offres_bp.route("/api/offres/<offre_id>", methods=["DELETE"])
@token_required
@permission_required('devis_delete')
def delete_offre(current_user_id, offre_id):
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
        message, status = handle_server_error(e, "suppression de l'offre")
        return jsonify(message), status


@offres_bp.route("/api/offres/stats", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_offres_stats(current_user_id):
    """Statistiques des offres"""
    try:
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
        message, status = handle_server_error(e, "récupération des statistiques")
        return jsonify({
            "total_offres": 0,
            "non_prepare_offres": 0,
            "en_preparation_offres": 0,
            "envoyee_offres": 0
        }), 200


@offres_bp.route("/api/panier/can-view", methods=["GET"])
@token_required
def can_view_panier(current_user_id):
    """Vérifier si l'utilisateur peut voir le menu panier - INDÉPENDANT des autres permissions"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_role = current_user.get('role') if current_user else None
        user_permissions = current_user.get('permissions', []) if current_user else []
        
        # Vérifier les permissions du panier - INDÉPENDANTE des autres permissions
        privileged_roles = ["admin", "supadmin", "administrateur principal", "administrateur système"]
        is_privileged = user_role.lower() in privileged_roles if user_role else False
        
        # La permission cart_view seule suffit pour voir le menu panier
        has_cart_view = is_privileged or 'cart_view' in user_permissions
        has_cart_view_all = is_privileged or 'cart_view_all' in user_permissions
        
        # Si l'utilisateur a cart_view OU cart_view_all, il peut voir le menu panier
        can_view = has_cart_view or has_cart_view_all
        
        return jsonify({
            "can_view": can_view,
            "has_cart_view": has_cart_view,
            "has_cart_view_all": has_cart_view_all,
            "permissions": user_permissions,
            "role": user_role
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "vérification de la permission panier")
        return jsonify({
            "can_view": False,
            "error": "Erreur lors de la vérification"
        }), status


@offres_bp.route("/api/test-offres", methods=["GET"])
def test_offres_connection():
    """Test de connexion à la collection offres"""
    try:
        # Test de connexion
        client.admin.command('ping')
        
        # Compter les éléments
        count = offres_col.count_documents({})
        
        # Récupérer quelques offres pour debug
        sample_offres = list(offres_col.find().limit(3))
        for offre in sample_offres:
            offre["_id"] = str(offre["_id"])
            if "responsable_id" in offre:
                offre["responsable_id"] = str(offre["responsable_id"])
        
        return jsonify({
            "status": "Offres OK",
            "message": f"Connexion à la collection offres réussie. {count} offres trouvées.",
            "count": count,
            "sample_offres": sample_offres
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "connexion à la collection offres")
        return jsonify({
            "status": "Offres Error",
            "message": "Erreur de connexion à la collection offres"
        }), status


@offres_bp.route("/api/test-update-offre/<offre_id>", methods=["PUT"])
def test_update_offre(offre_id):
    """Test de mise à jour d'offre avec les nouveaux champs"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Préparer les données de mise à jour
        update_data = {}
        
        # Gestion des nouveaux champs
        if "Catégorie" in data:
            update_data["categorie"] = data["Catégorie"]
        
        if "N-Offre" in data:
            update_data["numero"] = data["N-Offre"]
        
        if "Partenaire" in data:
            update_data["partenaire"] = data["Partenaire"]
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour l'offre
        result = offres_col.update_one(
            {"_id": ObjectId(offre_id)},
            {"$set": update_data}
        )
        
        # Récupérer l'offre mise à jour
        updated_offre = offres_col.find_one({"_id": ObjectId(offre_id)})
        if updated_offre:
            updated_offre["_id"] = str(updated_offre["_id"])
            if "responsable_id" in updated_offre:
                updated_offre["responsable_id"] = str(updated_offre["responsable_id"])
        
        return jsonify({
            "message": "Test de mise à jour réussi",
            "modified_count": result.modified_count,
            "updated_offre": updated_offre
        }), 200
        
    except Exception as e:
        message, status = handle_server_error(e, "test de mise à jour")
        return jsonify(message), status










