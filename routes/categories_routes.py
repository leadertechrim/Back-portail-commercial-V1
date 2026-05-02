"""Routes pour la gestion des catégories et statuts"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from bson.objectid import ObjectId
from database import (
    link_categories_col, offer_categories_col, links_col,
    quote_statuses_col, invoice_statuses_col, offer_statuses_col
)
from urllib.parse import urlparse
from utils.error_handler import handle_server_error

categories_bp = Blueprint('categories', __name__)


# ===== ROUTES POUR LES CATÉGORIES DE LIENS =====

@categories_bp.route('/api/link-categories', methods=['GET'])
def get_link_categories():
    """Récupérer toutes les catégories de liens"""
    try:
        categories = list(link_categories_col.find().sort("ordre", 1))
        # Convertir ObjectId en string pour JSON
        for category in categories:
            category['_id'] = str(category['_id'])
        return jsonify(categories)
    except Exception as e:
        print(f"Erreur lors de la récupération des catégories de liens: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/link-categories/<category_id>', methods=['GET'])
def get_link_category(category_id):
    """Récupérer une catégorie de lien par ID"""
    try:
        category = link_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        category['_id'] = str(category['_id'])
        return jsonify(category)
    except Exception as e:
        print(f"Erreur lors de la récupération de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/link-categories', methods=['POST'])
def create_link_category():
    """Créer une nouvelle catégorie de lien"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        # Validation
        if not nom or not couleur:
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        # Vérifier si la catégorie existe déjà
        existing = link_categories_col.find_one({"nom": nom})
        if existing:
            return jsonify({"message": "Cette catégorie existe déjà"}), 400
        
        # Calculer l'ordre
        count = link_categories_col.count_documents({})
        
        category_data = {
            "nom": nom,
            "description": data.get('description', ''),
            "couleur": couleur,
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = link_categories_col.insert_one(category_data)
        category_data['_id'] = str(result.inserted_id)
        return jsonify(category_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/link-categories/<category_id>', methods=['PUT'])
def update_link_category(category_id):
    """Modifier une catégorie de lien"""
    try:
        data = request.get_json()
        
        # Vérifier si la catégorie existe
        category = link_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        
        # Vérifier si le nouveau nom existe déjà (si différent)
        nom = data.get('nom')
        if nom and nom != category['nom']:
            existing = link_categories_col.find_one({"nom": nom})
            if existing:
                return jsonify({"message": "Cette catégorie existe déjà"}), 400
        
        # Mettre à jour
        update_data = {
            "nom": data.get('nom', category['nom']),
            "description": data.get('description', category['description']),
            "couleur": data.get('couleur', category['couleur']),
            "ordre": data.get('ordre', category['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        link_categories_col.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": update_data}
        )
        
        # Récupérer la catégorie mise à jour
        updated_category = link_categories_col.find_one({"_id": ObjectId(category_id)})
        updated_category['_id'] = str(updated_category['_id'])
        return jsonify(updated_category)
        
    except Exception as e:
        print(f"Erreur lors de la modification de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/link-categories/<category_id>', methods=['DELETE'])
def delete_link_category(category_id):
    """Supprimer une catégorie de lien"""
    try:
        category = link_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        
        link_categories_col.delete_one({"_id": ObjectId(category_id)})
        return jsonify({"message": "Catégorie supprimée avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


# ===== ROUTES POUR LES CATÉGORIES D'OFFRES =====

@categories_bp.route('/api/offer-categories', methods=['GET'])
def get_offer_categories():
    """Récupérer toutes les catégories d'offres"""
    try:
        categories = list(offer_categories_col.find().sort("ordre", 1))
        for category in categories:
            category['_id'] = str(category['_id'])
        return jsonify(categories)
    except Exception as e:
        print(f"Erreur lors de la récupération des catégories d'offres: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-categories/<category_id>', methods=['GET'])
def get_offer_category(category_id):
    """Récupérer une catégorie d'offre par ID"""
    try:
        category = offer_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        category['_id'] = str(category['_id'])
        return jsonify(category)
    except Exception as e:
        print(f"Erreur lors de la récupération de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-categories', methods=['POST'])
def create_offer_category():
    """Créer une nouvelle catégorie d'offre"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        if not nom or not couleur:
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        existing = offer_categories_col.find_one({"nom": nom})
        if existing:
            return jsonify({"message": "Cette catégorie existe déjà"}), 400
        
        count = offer_categories_col.count_documents({})
        
        category_data = {
            "nom": nom,
            "description": data.get('description', ''),
            "couleur": couleur,
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = offer_categories_col.insert_one(category_data)
        category_data['_id'] = str(result.inserted_id)
        return jsonify(category_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-categories/<category_id>', methods=['PUT'])
def update_offer_category(category_id):
    """Modifier une catégorie d'offre"""
    try:
        data = request.get_json()
        
        category = offer_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        
        nom = data.get('nom')
        if nom and nom != category['nom']:
            existing = offer_categories_col.find_one({"nom": nom})
            if existing:
                return jsonify({"message": "Cette catégorie existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', category['nom']),
            "description": data.get('description', category['description']),
            "couleur": data.get('couleur', category['couleur']),
            "ordre": data.get('ordre', category['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        offer_categories_col.update_one(
            {"_id": ObjectId(category_id)},
            {"$set": update_data}
        )
        
        updated_category = offer_categories_col.find_one({"_id": ObjectId(category_id)})
        updated_category['_id'] = str(updated_category['_id'])
        return jsonify(updated_category)
        
    except Exception as e:
        print(f"Erreur lors de la modification de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-categories/<category_id>', methods=['DELETE'])
def delete_offer_category(category_id):
    """Supprimer une catégorie d'offre"""
    try:
        category = offer_categories_col.find_one({"_id": ObjectId(category_id)})
        if not category:
            return jsonify({"message": "Catégorie non trouvée"}), 404
        
        offer_categories_col.delete_one({"_id": ObjectId(category_id)})
        return jsonify({"message": "Catégorie supprimée avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression de la catégorie: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


# ===== ROUTES POUR LES LIENS UTILES =====

@categories_bp.route('/api/links', methods=['GET'])
def get_links():
    """Récupérer tous les liens"""
    try:
        categorie = request.args.get('categorie')
        query = {}
        if categorie:
            query['categorie'] = categorie
        
        links = list(links_col.find(query).sort("ordre", 1))
        for link in links:
            link['_id'] = str(link['_id'])
        return jsonify(links)
    except Exception as e:
        print(f"Erreur lors de la récupération des liens: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/links/<link_id>', methods=['GET'])
def get_link(link_id):
    """Récupérer un lien par ID"""
    try:
        link = links_col.find_one({"_id": ObjectId(link_id)})
        if not link:
            return jsonify({"message": "Lien non trouvé"}), 404
        link['_id'] = str(link['_id'])
        return jsonify(link)
    except Exception as e:
        print(f"Erreur lors de la récupération du lien: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/links', methods=['POST'])
def create_link():
    """Créer un nouveau lien"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        url = data.get('url')
        categorie = data.get('categorie')
        
        if not nom or not url or not categorie:
            return jsonify({"message": "Nom, URL et catégorie sont requis"}), 400
        
        # Validation URL
        try:
            urlparse(url)
        except:
            return jsonify({"message": "URL invalide"}), 400
        
        # Vérifier si le lien existe déjà
        existing = links_col.find_one({"url": url})
        if existing:
            return jsonify({"message": "Ce lien existe déjà"}), 400
        
        count = links_col.count_documents({})
        
        link_data = {
            "nom": nom,
            "url": url,
            "categorie": categorie,
            "description": data.get('description', ''),
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = links_col.insert_one(link_data)
        link_data['_id'] = str(result.inserted_id)
        return jsonify(link_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création du lien: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/links/<link_id>', methods=['PUT'])
def update_link(link_id):
    """Modifier un lien"""
    try:
        data = request.get_json()
        
        link = links_col.find_one({"_id": ObjectId(link_id)})
        if not link:
            return jsonify({"message": "Lien non trouvé"}), 404
        
        # Validation URL si fournie
        url = data.get('url')
        if url:
            try:
                urlparse(url)
            except:
                return jsonify({"message": "URL invalide"}), 400
            
            if url != link['url']:
                existing = links_col.find_one({"url": url})
                if existing:
                    return jsonify({"message": "Ce lien existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', link['nom']),
            "url": data.get('url', link['url']),
            "categorie": data.get('categorie', link['categorie']),
            "description": data.get('description', link['description']),
            "ordre": data.get('ordre', link['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        links_col.update_one(
            {"_id": ObjectId(link_id)},
            {"$set": update_data}
        )
        
        updated_link = links_col.find_one({"_id": ObjectId(link_id)})
        updated_link['_id'] = str(updated_link['_id'])
        return jsonify(updated_link)
        
    except Exception as e:
        print(f"Erreur lors de la modification du lien: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/links/<link_id>', methods=['DELETE'])
def delete_link(link_id):
    """Supprimer un lien"""
    try:
        link = links_col.find_one({"_id": ObjectId(link_id)})
        if not link:
            return jsonify({"message": "Lien non trouvé"}), 404
        
        links_col.delete_one({"_id": ObjectId(link_id)})
        return jsonify({"message": "Lien supprimé avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression du lien: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


# ===== ROUTES POUR LES STATUTS DE DEVIS =====

@categories_bp.route('/api/quote-statuses', methods=['GET'])
def get_quote_statuses():
    """Récupérer tous les statuts de devis"""
    try:
        statuses = list(quote_statuses_col.find().sort("ordre", 1))
        for status in statuses:
            status['_id'] = str(status['_id'])
        return jsonify(statuses)
    except Exception as e:
        print(f"Erreur lors de la récupération des statuts de devis: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/quote-statuses/<status_id>', methods=['GET'])
def get_quote_status(status_id):
    """Récupérer un statut de devis par ID"""
    try:
        status = quote_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        status['_id'] = str(status['_id'])
        return jsonify(status)
    except Exception as e:
        print(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/quote-statuses', methods=['POST'])
def create_quote_status():
    """Créer un nouveau statut de devis"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        if not nom or not couleur:
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        existing = quote_statuses_col.find_one({"nom": nom})
        if existing:
            return jsonify({"message": "Ce statut existe déjà"}), 400
        
        count = quote_statuses_col.count_documents({})
        
        status_data = {
            "nom": nom,
            "couleur": couleur,
            "description": data.get('description', ''),
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = quote_statuses_col.insert_one(status_data)
        status_data['_id'] = str(result.inserted_id)
        return jsonify(status_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/quote-statuses/<status_id>', methods=['PUT'])
def update_quote_status(status_id):
    """Modifier un statut de devis"""
    try:
        data = request.get_json()
        
        status = quote_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        nom = data.get('nom')
        if nom and nom != status['nom']:
            existing = quote_statuses_col.find_one({"nom": nom})
            if existing:
                return jsonify({"message": "Ce statut existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', status['nom']),
            "couleur": data.get('couleur', status['couleur']),
            "description": data.get('description', status['description']),
            "ordre": data.get('ordre', status['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        quote_statuses_col.update_one(
            {"_id": ObjectId(status_id)},
            {"$set": update_data}
        )
        
        updated_status = quote_statuses_col.find_one({"_id": ObjectId(status_id)})
        updated_status['_id'] = str(updated_status['_id'])
        return jsonify(updated_status)
        
    except Exception as e:
        print(f"Erreur lors de la modification du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/quote-statuses/<status_id>', methods=['DELETE'])
def delete_quote_status(status_id):
    """Supprimer un statut de devis"""
    try:
        status = quote_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        quote_statuses_col.delete_one({"_id": ObjectId(status_id)})
        return jsonify({"message": "Statut supprimé avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


# ===== ROUTES POUR LES STATUTS DE FACTURES =====

@categories_bp.route('/api/invoice-statuses', methods=['GET'])
def get_invoice_statuses():
    """Récupérer tous les statuts de factures"""
    try:
        statuses = list(invoice_statuses_col.find().sort("ordre", 1))
        for status in statuses:
            status['_id'] = str(status['_id'])
        return jsonify(statuses)
    except Exception as e:
        print(f"Erreur lors de la récupération des statuts de factures: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/invoice-statuses/<status_id>', methods=['GET'])
def get_invoice_status(status_id):
    """Récupérer un statut de facture par ID"""
    try:
        status = invoice_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        status['_id'] = str(status['_id'])
        return jsonify(status)
    except Exception as e:
        print(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/invoice-statuses', methods=['POST'])
def create_invoice_status():
    """Créer un nouveau statut de facture"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        if not nom or not couleur:
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        existing = invoice_statuses_col.find_one({"nom": nom})
        if existing:
            return jsonify({"message": "Ce statut existe déjà"}), 400
        
        count = invoice_statuses_col.count_documents({})
        
        status_data = {
            "nom": nom,
            "couleur": couleur,
            "description": data.get('description', ''),
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = invoice_statuses_col.insert_one(status_data)
        status_data['_id'] = str(result.inserted_id)
        return jsonify(status_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/invoice-statuses/<status_id>', methods=['PUT'])
def update_invoice_status(status_id):
    """Modifier un statut de facture"""
    try:
        data = request.get_json()
        
        status = invoice_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        nom = data.get('nom')
        if nom and nom != status['nom']:
            existing = invoice_statuses_col.find_one({"nom": nom})
            if existing:
                return jsonify({"message": "Ce statut existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', status['nom']),
            "couleur": data.get('couleur', status['couleur']),
            "description": data.get('description', status['description']),
            "ordre": data.get('ordre', status['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        invoice_statuses_col.update_one(
            {"_id": ObjectId(status_id)},
            {"$set": update_data}
        )
        
        updated_status = invoice_statuses_col.find_one({"_id": ObjectId(status_id)})
        updated_status['_id'] = str(updated_status['_id'])
        return jsonify(updated_status)
        
    except Exception as e:
        print(f"Erreur lors de la modification du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/invoice-statuses/<status_id>', methods=['DELETE'])
def delete_invoice_status(status_id):
    """Supprimer un statut de facture"""
    try:
        status = invoice_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        invoice_statuses_col.delete_one({"_id": ObjectId(status_id)})
        return jsonify({"message": "Statut supprimé avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


# ===== ROUTES POUR LES STATUTS D'OFFRES =====

@categories_bp.route('/api/offer-statuses', methods=['GET'])
def get_offer_statuses():
    """Récupérer tous les statuts d'offres"""
    try:
        statuses = list(offer_statuses_col.find().sort("ordre", 1))
        for status in statuses:
            status['_id'] = str(status['_id'])
        return jsonify(statuses)
    except Exception as e:
        print(f"Erreur lors de la récupération des statuts d'offres: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-statuses/<status_id>', methods=['GET'])
def get_offer_status(status_id):
    """Récupérer un statut d'offre par ID"""
    try:
        status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        status['_id'] = str(status['_id'])
        return jsonify(status)
    except Exception as e:
        print(f"Erreur lors de la récupération du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500


@categories_bp.route('/api/offer-statuses', methods=['POST'])
def create_offer_status():
    """Créer un nouveau statut d'offre"""
    try:
        data = request.get_json()
        
        
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        if not nom or not couleur:
            print(f"ERROR: Nom ou couleur manquant - nom: {nom}, couleur: {couleur}")
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        existing = offer_statuses_col.find_one({"nom": nom})
        if existing:
            print(f"ERROR: Statut d'offre '{nom}' existe déjà")
            return jsonify({"message": "Ce statut existe déjà"}), 400
        
        count = offer_statuses_col.count_documents({})
        
        status_data = {
            "nom": nom,
            "couleur": couleur,
            "description": data.get('description', ''),
            "ordre": data.get('ordre', count + 1),
            "createdAt": datetime.utcnow(),
            "updatedAt": datetime.utcnow()
        }
        
        result = offer_statuses_col.insert_one(status_data)
        
        if result.inserted_id:
            status_data['_id'] = str(result.inserted_id)
            print(f"SUCCESS: Statut d'offre créé avec ID: {result.inserted_id}")
            return jsonify(status_data), 201
        else:
            print(f"ERROR: Échec de l'insertion dans la base de données")
            return jsonify({"message": "Échec de l'enregistrement"}), 500
        
    except Exception as e:
        message, status = handle_server_error(e, "création du statut d'offre")
        return jsonify(message), status


@categories_bp.route('/api/offer-statuses/<status_id>', methods=['PUT'])
def update_offer_status(status_id):
    """Modifier un statut d'offre"""
    try:
        data = request.get_json()
        
        
        status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            print(f"ERROR: Statut d'offre {status_id} non trouvé")
            return jsonify({"message": "Statut non trouvé"}), 404
        
        nom = data.get('nom')
        if nom and nom != status['nom']:
            existing = offer_statuses_col.find_one({"nom": nom})
            if existing:
                print(f"ERROR: Statut d'offre '{nom}' existe déjà")
                return jsonify({"message": "Ce statut existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', status['nom']),
            "couleur": data.get('couleur', status['couleur']),
            "description": data.get('description', status['description']),
            "ordre": data.get('ordre', status['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        result = offer_statuses_col.update_one(
            {"_id": ObjectId(status_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            updated_status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
            updated_status['_id'] = str(updated_status['_id'])
            print(f"SUCCESS: Statut d'offre {status_id} mis à jour")
            return jsonify(updated_status)
        else:
            print(f"WARNING: Aucune modification effectuée pour le statut {status_id}")
            updated_status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
            updated_status['_id'] = str(updated_status['_id'])
            return jsonify(updated_status)
        
    except Exception as e:
        message, status = handle_server_error(e, "modification du statut d'offre")
        return jsonify(message), status


@categories_bp.route('/api/offer-statuses/<status_id>', methods=['DELETE'])
def delete_offer_status(status_id):
    """Supprimer un statut d'offre"""
    try:
        
        status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            print(f"ERROR: Statut d'offre {status_id} non trouvé")
            return jsonify({"message": "Statut non trouvé"}), 404
        
        result = offer_statuses_col.delete_one({"_id": ObjectId(status_id)})
        
        if result.deleted_count > 0:
            print(f"SUCCESS: Statut d'offre {status_id} supprimé avec succès")
            return jsonify({"message": "Statut supprimé avec succès"})
        else:
            print(f"WARNING: Aucun document supprimé pour le statut {status_id}")
            return jsonify({"message": "Aucun document supprimé"}), 404
        
    except Exception as e:
        message, status = handle_server_error(e, "suppression du statut d'offre")
        return jsonify(message), status

