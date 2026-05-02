"""Routes pour la gestion des sources d'appels d'offres"""
from flask import Blueprint, request, jsonify
from bson.objectid import ObjectId
from database import sources_col
from auth.decorators import token_required, permission_required
from utils.error_handler import handle_server_error

sources_bp = Blueprint('sources', __name__)


# Fonctions utilitaires pour réorganiser les ordres
def reorganize_orders_on_update(categorie, old_order, new_order, entity_id):
    """Réorganise les ordres lors de la modification"""
    # Convertir en int pour éviter l'erreur de comparaison
    old_order = int(old_order) if old_order else 0
    new_order = int(new_order) if new_order else 0
    
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
    # Compter les éléments qui seront affectés
    count_before = sources_col.count_documents({
        "categorie": categorie,
        "order": {"$gte": new_order}
    })
    
    result = sources_col.update_many(
        {
            "categorie": categorie,
            "order": {"$gte": new_order}
        },
        {"$inc": {"order": 1}}
    )


@sources_bp.route("/api/sources", methods=["GET"])
@token_required
@permission_required('sources_view')
def get_sources(current_user_id):
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


@sources_bp.route("/api/recherche", methods=["GET"])
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


@sources_bp.route("/api/sources/check-duplicate", methods=["POST"])
@token_required
@permission_required('sources_view')
def check_duplicate_source(current_user_id):
    """Vérifier si une entité ou URL existe déjà (pour validation frontend)"""
    data = request.get_json()
    if not data:
        return jsonify({"message": "Données manquantes"}), 400
    
    nom_entite = data.get("nom_entite", "").strip()
    url = data.get("url", "").strip()
    source_id = data.get("source_id")  # Optionnel, pour exclure l'entité actuelle lors de la modification
    
    result = {
        "nom_entite_exists": False,
        "url_exists": False,
        "nom_entite_message": "",
        "url_message": ""
    }
    
    # Vérifier le nom_entite
    if nom_entite:
        query_entity = {"nom_entite": nom_entite}
        if source_id:
            try:
                query_entity["_id"] = {"$ne": ObjectId(source_id)}
            except:
                pass
        existing_entity = sources_col.find_one(query_entity)
        if existing_entity:
            result["nom_entite_exists"] = True
            result["nom_entite_message"] = f"Cette entité '{nom_entite}' existe déjà"
    
    # Vérifier l'URL
    if url:
        query_url = {"url": url}
        if source_id:
            try:
                query_url["_id"] = {"$ne": ObjectId(source_id)}
            except:
                pass
        existing_url = sources_col.find_one(query_url)
        if existing_url:
            result["url_exists"] = True
            result["url_message"] = f"Cette URL existe déjà pour l'entité '{existing_url.get('nom_entite', '')}'"
    
    return jsonify(result), 200


@sources_bp.route("/api/sources/grouped", methods=["GET"])
@token_required
@permission_required('sources_view')
def get_sources_grouped(current_user_id):
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

    # Récupérer les catégories existantes
    all_categories = sources_col.distinct("categorie")

    return jsonify({
        "nationale": fetch_block("Nationale"),
        "internationale": fetch_block("Internationale"),
        "debug_categories": all_categories  # Pour debug
    })


@sources_bp.route("/api/sources", methods=["POST"])
@token_required
@permission_required('sources_create')
def add_source(current_user_id):
    data = request.get_json()
    if not all([data.get("nom_entite"), data.get("url"), data.get("categorie")]):
        return jsonify({"message": "Champs manquants"}), 400
    
    nom_entite = data.get("nom_entite", "").strip()
    url = data.get("url", "").strip()
    
    # Vérifier si l'entité (nom_entite) existe déjà - BLOQUER si redondant
    existing_entity = sources_col.find_one({"nom_entite": nom_entite})
    if existing_entity:
        return jsonify({
            "message": f"Cette entité '{nom_entite}' existe déjà",
            "error": "duplicate_entity",
            "existing_id": str(existing_entity["_id"])
        }), 409
    
    # Vérifier si l'URL (lien) existe déjà - BLOQUER si redondant
    existing_url = sources_col.find_one({"url": url})
    if existing_url:
        return jsonify({
            "message": f"Cette URL existe déjà pour l'entité '{existing_url.get('nom_entite', '')}'",
            "error": "duplicate_url",
            "existing_id": str(existing_url["_id"])
        }), 409
    
    # Réorganiser les ordres AVANT l'insertion
    try:
        new_order = int(data.get("order", 1))
        categorie = data.get("categorie")
        if categorie:
            reorganize_orders_on_insert(categorie, new_order)
        
        # S'assurer que l'ordre est bien un entier dans les données insérées
        data["order"] = new_order
        
        sources_col.insert_one(data)
        return jsonify({"message": "Source ajoutée"}), 201
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout de la source: {str(e)}")
        return jsonify({
            "message": "Erreur lors de l'ajout de la source",
            "error": str(e)
        }), 500



@sources_bp.route("/api/sources/<source_id>", methods=["PUT"])
@token_required
@permission_required('sources_edit')
def update_source(current_user_id, source_id):
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
    
    nom_entite = data.get("nom_entite", "").strip() if data.get("nom_entite") else old_entity.get("nom_entite", "").strip()
    url = data.get("url", "").strip() if data.get("url") else old_entity.get("url", "").strip()
    
    # Vérifier si le nouveau nom_entite existe déjà (sauf pour l'entité actuelle) - BLOQUER si redondant
    if nom_entite and nom_entite != old_entity.get("nom_entite", ""):
        existing_entity = sources_col.find_one({
            "nom_entite": nom_entite,
            "_id": {"$ne": ObjectId(source_id)}
        })
        if existing_entity:
            return jsonify({
                "message": f"Cette entité '{nom_entite}' existe déjà",
                "error": "duplicate_entity",
                "existing_id": str(existing_entity["_id"])
            }), 409
    
    # Vérifier si la nouvelle URL existe déjà (sauf pour l'entité actuelle) - BLOQUER si redondant
    if url and url != old_entity.get("url", ""):
        existing_url = sources_col.find_one({
            "url": url,
            "_id": {"$ne": ObjectId(source_id)}
        })
        if existing_url:
            return jsonify({
                "message": f"Cette URL existe déjà pour l'entité '{existing_url.get('nom_entite', '')}'",
                "error": "duplicate_url",
                "existing_id": str(existing_url["_id"])
            }), 409
    
    old_order = int(old_entity.get("order", 0))
    new_order = int(data.get("order", old_order))
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
    
    # Mettre à jour l'entité (sans le _id)
    update_data = {k: v for k, v in data.items() if k != '_id'}
    sources_col.update_one(
        {"_id": ObjectId(source_id)},
        {"$set": update_data}
    )
    return jsonify({"message": "Source mise à jour"}), 200


@sources_bp.route("/api/sources/<source_id>", methods=["DELETE"])
@token_required
@permission_required('sources_delete')
def delete_source(current_user_id, source_id):
    # Récupérer l'entité avant suppression pour réorganiser les ordres
    try:
        entity = sources_col.find_one({"_id": ObjectId(source_id)})
        if not entity:
            return jsonify({"message": "Source non trouvée"}), 404
        
        old_order = int(entity.get("order", 0))
        categorie = entity.get("categorie")
        
        # Supprimer la source
        sources_col.delete_one({"_id": ObjectId(source_id)})
        
        # Réorganiser : décaler toutes les sources après vers le haut (-1)
        sources_col.update_many(
            {
                "categorie": categorie,
                "order": {"$gt": old_order}
            },
            {"$inc": {"order": -1}}
        )
        
        return jsonify({"message": "Source supprimée"}), 200
    except Exception as e:
        message, status = handle_server_error(e, "suppression de la source")
        return jsonify(message), status










