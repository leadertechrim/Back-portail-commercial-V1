import os
import re
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
import jwt
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from functools import wraps

app = Flask(__name__)

# Configuration CORS simple et efficace
CORS(app, origins=['*'], supports_credentials=True)
bcrypt = Bcrypt(app)

# Configuration sécurisée
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://Emama:N8F7kSlWoJpZ0bIk@cluster0.1czao7m.mongodb.net/?retryWrites=true&w=majority")
# MongoDB
client = MongoClient(MONGO_URI)
db = client.appels_doffres_db_copy
sources_col = db.appels_doffres_sourcess  # Collection avec double 's' comme dans votre base
users_col = db.users
offres_col = db.offres
calls_for_tender_col = db.calls_for_tender
clients_col = db.Clients
partenaires_col = db.Partenaires
personnels_col = db.Personnels
devis_col = db.devis
factures_col = db.factures

# Nouvelles collections
link_categories_col = db.link_categories
offer_categories_col = db.offer_categories
links_col = db.links
quote_statuses_col = db.quote_statuses
invoice_statuses_col = db.invoice_statuses
offer_statuses_col = db.offer_statuses

# Collections pour les rôles et permissions
roles_collection = db.roles
permissions_collection = db.permissions

# =============================================================================
# FONCTIONS UTILITAIRES POUR LES RÔLES ET PERMISSIONS
# =============================================================================

def token_required(f):
    """Décorateur pour vérifier le token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'message': 'Token manquant'}), 401
        
        try:
            token = token[7:]  # Enlever "Bearer "
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expiré'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token invalide'}), 401
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def permission_required(permission_name):
    """Décorateur pour vérifier une permission spécifique"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user_id, *args, **kwargs):
            user = users_col.find_one({'_id': ObjectId(current_user_id)})
            if not user:
                return jsonify({'message': 'Utilisateur non trouvé'}), 404
            
            if not user_has_permission(user, permission_name):
                return jsonify({'message': f'Permission "{permission_name}" requise'}), 403
            
            return f(current_user_id, *args, **kwargs)
        return decorated
    return decorator

def user_has_permission(user, permission_name):
    """Vérifie si un utilisateur a une permission spécifique"""
    # Les admins ont toutes les permissions
    if user.get('role') == 'admin':
        return True
    
    # Récupérer les permissions du rôle depuis la base - chercher par nom
    user_role = user.get('role', 'spectateur')
    role = roles_collection.find_one({'nom': user_role})
    if role:
        return permission_name in role.get('permissions', [])
    
    return False

def get_user_permissions(user):
    """Récupère toutes les permissions d'un utilisateur"""
    if user.get('role') == 'admin':
        return [p['nom'] for p in permissions_collection.find()]
    
    # Récupérer les permissions du rôle depuis la base - chercher par nom
    user_role = user.get('role', 'spectateur')
    role = roles_collection.find_one({'nom': user_role})
    if role:
        return role.get('permissions', [])
    
    return []

def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    @wraps(f)
    def decorated(current_user_id, *args, **kwargs):
        user = users_col.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        if user.get('role') != 'admin':
            return jsonify({'message': 'Accès administrateur requis'}), 403
        
        return f(current_user_id, *args, **kwargs)
    return decorated

def validate_role_data(data):
    """Valider les données d'un rôle"""
    errors = []
    
    if not data.get('nom'):
        errors.append('Le nom du rôle est requis')
    elif len(data['nom']) < 2:
        errors.append('Le nom du rôle doit contenir au moins 2 caractères')
    elif not re.match(r'^[a-zA-Z0-9_-]+$', data['nom']):
        errors.append('Le nom du rôle ne peut contenir que des lettres, chiffres, tirets et underscores')
    
    if data.get('description') and len(data['description']) > 500:
        errors.append('La description ne peut pas dépasser 500 caractères')
    
    if data.get('couleur') and not re.match(r'^#[0-9A-Fa-f]{6}$', data['couleur']):
        errors.append('La couleur doit être au format hexadécimal (#RRGGBB)')
    
    if data.get('ordre') and (not isinstance(data['ordre'], int) or data['ordre'] < 1):
        errors.append('L\'ordre doit être un nombre entier positif')
    
    if data.get('permissions') and not isinstance(data['permissions'], list):
        errors.append('Les permissions doivent être une liste')
    
    return errors

def validate_permission_data(data):
    """Valider les données d'une permission"""
    errors = []
    
    if not data.get('nom'):
        errors.append('Le nom de la permission est requis')
    elif len(data['nom']) < 3:
        errors.append('Le nom de la permission doit contenir au moins 3 caractères')
    elif not re.match(r'^[a-zA-Z0-9_-]+$', data['nom']):
        errors.append('Le nom de la permission ne peut contenir que des lettres, chiffres, tirets et underscores')
    
    if not data.get('description'):
        errors.append('La description de la permission est requise')
    elif len(data['description']) > 200:
        errors.append('La description ne peut pas dépasser 200 caractères')
    
    if not data.get('category'):
        errors.append('La catégorie de la permission est requise')
    elif len(data['category']) > 100:
        errors.append('La catégorie ne peut pas dépasser 100 caractères')
    
    return errors

def validate_user_role_assignment(user_id, role_name):
    """Valider l'assignation d'un rôle à un utilisateur"""
    errors = []
    
    if not ObjectId.is_valid(user_id):
        errors.append('ID utilisateur invalide')
    
    if not role_name:
        errors.append('Nom du rôle requis')
    
    # Vérifier que le rôle existe
    if role_name and not roles_collection.find_one({'nom': role_name}):
        errors.append('Le rôle spécifié n\'existe pas')
    
    # Vérifier que l'utilisateur existe
    if ObjectId.is_valid(user_id) and not users_col.find_one({'_id': ObjectId(user_id)}):
        errors.append('L\'utilisateur spécifié n\'existe pas')
    
    return errors

def sanitize_input(data):
    """Nettoyer les données d'entrée"""
    if isinstance(data, dict):
        return {k: sanitize_input(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_input(item) for item in data]
    elif isinstance(data, str):
        # Supprimer les caractères dangereux
        return data.strip().replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#x27;')
    else:
        return data

def rate_limit_check(user_id, action, limit=10, window=60):
    """Vérifier les limites de taux pour éviter les abus"""
    from datetime import datetime, timedelta
    
    # Cette fonction pourrait être implémentée avec Redis ou une base de données
    # Pour l'instant, on retourne True (pas de limite)
    return True

def audit_log(user_id, action, details=None):
    """Enregistrer les actions dans un log d'audit"""
    try:
        audit_data = {
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'timestamp': datetime.utcnow(),
            'ip_address': request.remote_addr if request else None
        }
        
        # Ici vous pourriez sauvegarder dans une collection d'audit
        # audit_collection.insert_one(audit_data)
        
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'audit: {e}")

# =============================================================================
# ROUTES POUR LES RÔLES
# =============================================================================

@app.route("/api/roles", methods=["GET"])
@token_required
def get_roles(current_user_id):
    """Récupérer tous les rôles"""
    try:
        roles = list(roles_collection.find().sort("ordre", 1))
        for role in roles:
            role['_id'] = str(role['_id'])
        
        return jsonify({
            'message': 'Rôles récupérés avec succès',
            'data': roles
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la récupération des rôles',
            'error': str(e)
        }), 500

@app.route("/api/roles/<role_id>", methods=["GET"])
@token_required
def get_role(current_user_id, role_id):
    """Récupérer un rôle par ID"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        role['_id'] = str(role['_id'])
        return jsonify({
            'message': 'Rôle récupéré avec succès',
            'data': role
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la récupération du rôle',
            'error': str(e)
        }), 500

@app.route("/api/roles", methods=["POST"])
@token_required
@permission_required('roles_manage')
def create_role(current_user_id):
    """Créer un rôle (admin seulement)"""
    try:
        data = request.get_json()
        
        # Nettoyer les données d'entrée
        data = sanitize_input(data)
        
        # Validation des données
        validation_errors = validate_role_data(data)
        if validation_errors:
            return jsonify({
                'message': 'Erreurs de validation',
                'errors': validation_errors
            }), 400
        
        # Vérifier les limites de taux
        if not rate_limit_check(current_user_id, 'create_role'):
            return jsonify({'message': 'Trop de requêtes. Veuillez patienter.'}), 429
        
        # Vérifier si le rôle existe déjà
        existing_role = roles_collection.find_one({'nom': data['nom']})
        if existing_role:
            return jsonify({'message': 'Un rôle avec ce nom existe déjà'}), 400
        
        # Récupérer l'ordre maximum
        max_order = roles_collection.find().sort("ordre", -1).limit(1)
        next_order = 1
        for role in max_order:
            next_order = role.get('ordre', 0) + 1
            break
        
        # Créer le rôle
        role_data = {
            'nom': data['nom'],
            'description': data.get('description', ''),
            'couleur': data.get('couleur', '#6c757d'),
            'ordre': data.get('ordre', next_order),
            'permissions': data.get('permissions', []),
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
        
        result = roles_collection.insert_one(role_data)
        role_data['_id'] = str(result.inserted_id)
        
        # Enregistrer l'audit
        audit_log(current_user_id, 'create_role', {'role_name': data['nom']})
        
        return jsonify({
            'message': 'Rôle créé avec succès',
            'data': role_data
        }), 201
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la création du rôle',
            'error': str(e)
        }), 500

@app.route("/api/roles/<role_id>", methods=["PUT"])
@token_required
@permission_required('roles_manage')
def update_role(current_user_id, role_id):
    """Modifier un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        
        # Vérifier si le rôle existe
        existing_role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not existing_role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        # Vérifier si le nom est déjà utilisé par un autre rôle
        old_role_name = existing_role['nom']
        new_role_name = data.get('nom', old_role_name)
        
        if new_role_name != old_role_name:
            duplicate_role = roles_collection.find_one({
                'nom': new_role_name,
                '_id': {'$ne': ObjectId(role_id)}
            })
            if duplicate_role:
                return jsonify({'message': 'Un rôle avec ce nom existe déjà'}), 400
            
            # ⭐ IMPORTANT : Mettre à jour tous les utilisateurs qui ont ce rôle
            print(f"🔄 Renommage du rôle '{old_role_name}' → '{new_role_name}'")
            result = users_col.update_many(
                {'role': old_role_name},
                {'$set': {'role': new_role_name}}
            )
            print(f"✅ {result.modified_count} utilisateur(s) mis à jour avec le nouveau nom de rôle")
        
        # Mettre à jour le rôle
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        allowed_fields = ['nom', 'description', 'couleur', 'ordre', 'permissions']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        roles_collection.update_one(
            {'_id': ObjectId(role_id)},
            {'$set': update_data}
        )
        
        # Récupérer le rôle mis à jour
        updated_role = roles_collection.find_one({'_id': ObjectId(role_id)})
        updated_role['_id'] = str(updated_role['_id'])
        
        return jsonify({
            'message': 'Rôle modifié avec succès',
            'data': updated_role
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la modification du rôle',
            'error': str(e)
        }), 500

@app.route("/api/roles/<role_id>", methods=["DELETE"])
@token_required
@permission_required('roles_manage')
def delete_role(current_user_id, role_id):
    """Supprimer un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        # Vérifier si le rôle existe
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        # Vérifier si des utilisateurs utilisent ce rôle (par nom, pas par code)
        role_name = role.get('nom', role.get('code', ''))
        users_with_role = users_col.count_documents({'role': role_name})
        print(f"DEBUG: Vérification suppression rôle '{role_name}' - {users_with_role} utilisateurs")
        
        if users_with_role > 0:
            return jsonify({
                'message': f'Impossible de supprimer le rôle. {users_with_role} utilisateur(s) l\'utilisent encore'
            }), 400
        
        # Supprimer le rôle
        roles_collection.delete_one({'_id': ObjectId(role_id)})
        
        return jsonify({
            'message': 'Rôle supprimé avec succès'
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la suppression du rôle',
            'error': str(e)
        }), 500

# =============================================================================
# ROUTES POUR LES PERMISSIONS
# =============================================================================

@app.route("/api/permissions", methods=["GET"])
@token_required
def get_permissions(current_user_id):
    """Récupérer toutes les permissions"""
    try:
        permissions = list(permissions_collection.find().sort("category", 1))
        print(f"Liste: Nombre de permissions trouvées: {len(permissions)}")
        if permissions:
            print(f"Debug: Premier élément de permission: {permissions[0]}")
            print(f"Debug: Clés du premier élément: {list(permissions[0].keys())}")
        
        for permission in permissions:
            permission['_id'] = str(permission['_id'])
        
        return jsonify({
            'message': 'Permissions récupérées avec succès',
            'data': permissions
        }), 200
    except Exception as e:
        print(f"ERREUR: Erreur lors de la récupération des permissions: {str(e)}")
        return jsonify({
            'message': 'Erreur lors de la récupération des permissions',
            'error': str(e)
        }), 500

@app.route("/api/user/permissions", methods=["GET"])
@token_required
def get_current_user_permissions(current_user_id):
    """Récupérer les permissions de l'utilisateur actuel"""
    try:
        # Récupérer les informations de l'utilisateur depuis la base de données
        user = users_col.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            print(f"ERREUR: Utilisateur avec ID {current_user_id} non trouvé")
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get("role")
        print(f"Role utilisateur: {user_role}")
        print(f"Role: User ID: {current_user_id}")
        
        # Debug: Vérifier tous les rôles dans la base
        all_roles = list(roles_collection.find())
        print(f"Debug: Tous les rôles dans la base: {[r.get('nom') for r in all_roles]}")
        
        # Trouver le rôle dans la base de données par nom (pas par code)
        role_doc = roles_collection.find_one({"nom": user_role})
        print(f"Recherche du role '{user_role}': {role_doc is not None}")
        
        if not role_doc:
            print(f"Role {user_role} non trouve dans la base")
            return jsonify({"message": "Role non trouve"}), 404
            
        # Retourner les permissions du rôle
        permissions = role_doc.get("permissions", [])
        
        print(f"OK: Permissions pour {user_role}: {len(permissions)} permissions")
        print(f"Liste: Premières permissions: {permissions[:3]}...")
        
        return jsonify({
            "message": "Permissions récupérées avec succès",
            "data": {
                "permissions": permissions,
                "role": user_role,
                "user_id": current_user_id
            }
        })
        
    except Exception as e:
        print(f"ERREUR: Erreur lors de la récupération des permissions: {e}")
        return jsonify({"message": f"Erreur serveur: {str(e)}"}), 500

@app.route("/api/users/<user_id>/permissions", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_user_permissions_by_id(current_user_id, user_id):
    """Récupérer les permissions d'un utilisateur spécifique (admin seulement)"""
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'ID utilisateur invalide'}), 400
        
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        permissions = get_user_permissions(user)
        
        return jsonify({
            'message': 'Permissions récupérées avec succès',
            'data': {
                'user_id': str(user['_id']),
                'name': user.get('name', ''),
                'email': user.get('email', ''),
                'role': user.get('role', 'spectateur'),
                'permissions': permissions
            }
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la récupération des permissions',
            'error': str(e)
        }), 500

# =============================================================================
# ROUTES POUR L'ASSIGNATION DES RÔLES
# =============================================================================

@app.route("/api/users/<user_id>/assign-role", methods=["POST"])
@token_required
@permission_required('users_manage')
def assign_role_to_user(current_user_id, user_id):
    """Assigner un rôle à un utilisateur (admin seulement)"""
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'ID utilisateur invalide'}), 400
        
        data = request.get_json()
        if 'role' not in data:
            return jsonify({'message': 'Champ "role" requis'}), 400
        
        # Vérifier si l'utilisateur existe
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        # Vérifier si le rôle existe
        role = roles_collection.find_one({'nom': data['role']})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        # Mettre à jour le rôle de l'utilisateur
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'role': data['role'], 'updated_at': datetime.utcnow()}}
        )
        
        # Récupérer l'utilisateur mis à jour
        updated_user = users_col.find_one({'_id': ObjectId(user_id)})
        updated_user['_id'] = str(updated_user['_id'])
        
        return jsonify({
            'message': 'Rôle assigné avec succès',
            'data': {
                'user_id': str(updated_user['_id']),
                'name': updated_user.get('name', ''),
                'email': updated_user.get('email', ''),
                'role': updated_user.get('role', 'spectateur')
            }
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de l\'assignation du rôle',
            'error': str(e)
        }), 500

@app.route("/api/users/<user_id>/remove-role", methods=["POST"])
@token_required
@permission_required('users_manage')
def remove_role_from_user(current_user_id, user_id):
    """Retirer un rôle d'un utilisateur (admin seulement)"""
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'ID utilisateur invalide'}), 400
        
        # Vérifier si l'utilisateur existe
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        # Assigner le rôle spectateur par défaut
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'role': 'spectateur', 'updated_at': datetime.utcnow()}}
        )
        
        # Récupérer l'utilisateur mis à jour
        updated_user = users_col.find_one({'_id': ObjectId(user_id)})
        updated_user['_id'] = str(updated_user['_id'])
        
        return jsonify({
            'message': 'Rôle retiré avec succès (rôle spectateur assigné)',
            'data': {
                'user_id': str(updated_user['_id']),
                'name': updated_user.get('name', ''),
                'email': updated_user.get('email', ''),
                'role': updated_user.get('role', 'spectateur')
            }
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la suppression du rôle',
            'error': str(e)
        }), 500

# =============================================================================
# ROUTES UTILITAIRES
# =============================================================================

@app.route("/api/roles/init", methods=["POST"])
@token_required
@permission_required('roles_manage')
def init_roles_and_permissions(current_user_id):
    """Initialiser les rôles et permissions par défaut (admin seulement)"""
    try:
        # Supprimer les collections existantes
        roles_collection.drop()
        permissions_collection.drop()
        
        # Créer les permissions
        permissions_data = [
            # Offres
            {"nom": "view_offers", "description": "Voir les offres", "category": "Offres"},
            {"nom": "create_offers", "description": "Créer des offres", "category": "Offres"},
            {"nom": "edit_offers", "description": "Modifier les offres", "category": "Offres"},
            {"nom": "delete_offers", "description": "Supprimer les offres", "category": "Offres"},
            
            # Devis
            {"nom": "view_quotes", "description": "Voir les devis", "category": "Devis"},
            {"nom": "create_quotes", "description": "Créer des devis", "category": "Devis"},
            {"nom": "edit_quotes", "description": "Modifier les devis", "category": "Devis"},
            {"nom": "delete_quotes", "description": "Supprimer les devis", "category": "Devis"},
            
            # Factures
            {"nom": "view_invoices", "description": "Voir les factures", "category": "Factures"},
            {"nom": "create_invoices", "description": "Créer des factures", "category": "Factures"},
            {"nom": "edit_invoices", "description": "Modifier les factures", "category": "Factures"},
            {"nom": "delete_invoices", "description": "Supprimer les factures", "category": "Factures"},
            
            # Clients
            {"nom": "view_clients", "description": "Voir les clients", "category": "Clients"},
            {"nom": "create_clients", "description": "Créer des clients", "category": "Clients"},
            {"nom": "edit_clients", "description": "Modifier les clients", "category": "Clients"},
            {"nom": "delete_clients", "description": "Supprimer les clients", "category": "Clients"},
            
            # Personnel
            {"nom": "view_personnel", "description": "Voir le personnel", "category": "Personnel"},
            {"nom": "create_personnel", "description": "Créer du personnel", "category": "Personnel"},
            {"nom": "edit_personnel", "description": "Modifier le personnel", "category": "Personnel"},
            {"nom": "delete_personnel", "description": "Supprimer le personnel", "category": "Personnel"},
            
            # Partenaires
            {"nom": "view_partners", "description": "Voir les partenaires", "category": "Partenaires"},
            {"nom": "create_partners", "description": "Créer des partenaires", "category": "Partenaires"},
            {"nom": "edit_partners", "description": "Modifier les partenaires", "category": "Partenaires"},
            {"nom": "delete_partners", "description": "Supprimer les partenaires", "category": "Partenaires"},
            
            # Sources
            {"nom": "view_sources", "description": "Voir les sources", "category": "Sources"},
            {"nom": "create_sources", "description": "Créer des sources", "category": "Sources"},
            {"nom": "edit_sources", "description": "Modifier les sources", "category": "Sources"},
            {"nom": "delete_sources", "description": "Supprimer les sources", "category": "Sources"},
            
            # Administration
            {"nom": "admin_settings", "description": "Gérer les paramètres", "category": "Administration"},
            {"nom": "manage_users", "description": "Gérer les utilisateurs", "category": "Administration"},
            {"nom": "manage_roles", "description": "Gérer les rôles", "category": "Administration"},
            {"nom": "view_analytics", "description": "Voir les analyses", "category": "Administration"},
            
            # Rapports
            {"nom": "view_reports", "description": "Voir les rapports", "category": "Rapports"},
            {"nom": "export_data", "description": "Exporter les données", "category": "Rapports"}
        ]
        
        for perm in permissions_data:
            perm['created_at'] = datetime.utcnow()
        
        permissions_collection.insert_many(permissions_data)
        
        # Créer les rôles
        roles_data = [
            {
                "nom": "admin",
                "description": "Administrateur avec tous les droits",
                "couleur": "#dc3545",
                "ordre": 1,
                "permissions": [p['nom'] for p in permissions_data],  # Toutes les permissions
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "nom": "user",
                "description": "Utilisateur standard avec accès principal",
                "couleur": "#007bff",
                "ordre": 2,
                "permissions": [
                    "view_offers", "create_offers", "edit_offers",
                    "view_quotes", "create_quotes", "edit_quotes",
                    "view_invoices", "create_invoices", "edit_invoices",
                    "view_clients", "create_clients", "edit_clients",
                    "view_personnel", "create_personnel", "edit_personnel",
                    "view_partners", "create_partners", "edit_partners",
                    "view_sources", "create_sources", "edit_sources",
                    "view_reports", "export_data"
                ],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            },
            {
                "nom": "spectateur",
                "description": "Lecteur avec accès en lecture seule",
                "couleur": "#6c757d",
                "ordre": 3,
                "permissions": [
                    "view_offers", "view_quotes", "view_invoices"
                ],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        ]
        
        roles_collection.insert_many(roles_data)
        
        return jsonify({
            'message': 'Rôles et permissions initialisés avec succès',
            'data': {
                'permissions_created': len(permissions_data),
                'roles_created': len(roles_data)
            }
        }), 201
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de l\'initialisation',
            'error': str(e)
        }), 500

@app.route("/api/test-permission/<permission_name>", methods=["GET"])
@token_required
def test_permission(current_user_id, permission_name):
    """Tester une permission pour l'utilisateur actuel"""
    try:
        user = users_col.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        has_permission = user_has_permission(user, permission_name)
        
        return jsonify({
            'message': 'Test de permission effectué',
            'data': {
                'permission': permission_name,
                'has_permission': has_permission,
                'user_role': user.get('role', 'spectateur')
            }
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors du test de permission',
            'error': str(e)
        }), 500

@app.route("/api/users-with-roles", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_users_with_roles(current_user_id):
    """Récupérer tous les utilisateurs avec leurs rôles (admin seulement)"""
    try:
        users = list(users_col.find({}, {'password': 0}).sort("name", 1))
        
        for user in users:
            user['_id'] = str(user['_id'])
            user['permissions'] = get_user_permissions(user)
        
        return jsonify({
            'message': 'Utilisateurs récupérés avec succès',
            'data': users
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la récupération des utilisateurs',
            'error': str(e)
        }), 500


# =============================================================================
# ROUTES POUR LA GESTION DYNAMIQUE DES PERMISSIONS
# =============================================================================

@app.route("/api/permissions", methods=["POST"])
@token_required
@permission_required('roles_manage')
def create_permission(current_user_id):
    """Créer une nouvelle permission (admin seulement)"""
    try:
        data = request.get_json()
        
        # Validation des données
        required_fields = ['nom', 'description', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Champ "{field}" requis'}), 400
        
        # Vérifier si la permission existe déjà
        existing_permission = permissions_collection.find_one({'nom': data['nom']})
        if existing_permission:
            return jsonify({'message': 'Une permission avec ce nom existe déjà'}), 400
        
        # Créer la permission
        permission_data = {
            'nom': data['nom'],
            'description': data['description'],
            'category': data['category'],
            'created_at': datetime.utcnow()
        }
        
        result = permissions_collection.insert_one(permission_data)
        permission_data['_id'] = str(result.inserted_id)
        
        return jsonify({
            'message': 'Permission créée avec succès',
            'data': permission_data
        }), 201
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la création de la permission',
            'error': str(e)
        }), 500

@app.route("/api/permissions/<permission_id>", methods=["PUT"])
@token_required
@permission_required('roles_manage')
def update_permission(current_user_id, permission_id):
    """Modifier une permission (admin seulement)"""
    try:
        if not ObjectId.is_valid(permission_id):
            return jsonify({'message': 'ID de permission invalide'}), 400
        
        data = request.get_json()
        
        # Vérifier si la permission existe
        existing_permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        if not existing_permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        # Vérifier si le nom est déjà utilisé par une autre permission
        if 'nom' in data and data['nom'] != existing_permission['nom']:
            duplicate_permission = permissions_collection.find_one({
                'nom': data['nom'],
                '_id': {'$ne': ObjectId(permission_id)}
            })
            if duplicate_permission:
                return jsonify({'message': 'Une permission avec ce nom existe déjà'}), 400
        
        # Mettre à jour la permission
        update_data = {}
        allowed_fields = ['nom', 'description', 'category']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        permissions_collection.update_one(
            {'_id': ObjectId(permission_id)},
            {'$set': update_data}
        )
        
        # Récupérer la permission mise à jour
        updated_permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        updated_permission['_id'] = str(updated_permission['_id'])
        
        return jsonify({
            'message': 'Permission modifiée avec succès',
            'data': updated_permission
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la modification de la permission',
            'error': str(e)
        }), 500

@app.route("/api/permissions/<permission_id>", methods=["DELETE"])
@token_required
@permission_required('roles_manage')
def delete_permission(current_user_id, permission_id):
    """Supprimer une permission (admin seulement)"""
    try:
        if not ObjectId.is_valid(permission_id):
            return jsonify({'message': 'ID de permission invalide'}), 400
        
        # Vérifier si la permission existe
        permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        if not permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        # Vérifier si des rôles utilisent cette permission
        roles_with_permission = roles_collection.count_documents({
            'permissions': permission['nom']
        })
        if roles_with_permission > 0:
            return jsonify({
                'message': f'Impossible de supprimer la permission. {roles_with_permission} rôle(s) l\'utilisent encore'
            }), 400
        
        # Supprimer la permission
        permissions_collection.delete_one({'_id': ObjectId(permission_id)})
        
        return jsonify({
            'message': 'Permission supprimée avec succès'
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la suppression de la permission',
            'error': str(e)
        }), 500

# =============================================================================
# ROUTES POUR LA GESTION DYNAMIQUE AVANCÉE
# =============================================================================

@app.route("/api/roles/<role_id>/permissions", methods=["POST"])
@token_required
@permission_required('roles_manage')
def add_permission_to_role(current_user_id, role_id):
    """Ajouter une permission à un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        if 'permission' not in data:
            return jsonify({'message': 'Champ "permission" requis'}), 400
        
        # Vérifier si le rôle existe
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        # Vérifier si la permission existe
        permission = permissions_collection.find_one({'nom': data['permission']})
        if not permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        # Ajouter la permission au rôle si elle n'y est pas déjà
        if data['permission'] not in role.get('permissions', []):
            roles_collection.update_one(
                {'_id': ObjectId(role_id)},
                {'$push': {'permissions': data['permission']}, '$set': {'updated_at': datetime.utcnow()}}
            )
        
        return jsonify({
            'message': 'Permission ajoutée au rôle avec succès'
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de l\'ajout de la permission',
            'error': str(e)
        }), 500

@app.route("/api/roles/<role_id>/permissions", methods=["DELETE"])
@token_required
@permission_required('roles_manage')
def remove_permission_from_role(current_user_id, role_id):
    """Retirer une permission d'un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        if 'permission' not in data:
            return jsonify({'message': 'Champ "permission" requis'}), 400
        
        # Vérifier si le rôle existe
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        # Retirer la permission du rôle
        roles_collection.update_one(
            {'_id': ObjectId(role_id)},
            {'$pull': {'permissions': data['permission']}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        return jsonify({
            'message': 'Permission retirée du rôle avec succès'
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la suppression de la permission',
            'error': str(e)
        }), 500

@app.route("/api/roles/bulk-update", methods=["POST"])
@token_required
@permission_required('roles_manage')
def bulk_update_roles(current_user_id):
    """Mise à jour en lot des rôles (admin seulement)"""
    try:
        data = request.get_json()
        if 'roles' not in data:
            return jsonify({'message': 'Champ "roles" requis'}), 400
        
        updated_count = 0
        errors = []
        
        for role_data in data['roles']:
            try:
                if '_id' not in role_data:
                    errors.append(f'Rôle sans ID: {role_data.get("nom", "Inconnu")}')
                    continue
                
                role_id = role_data['_id']
                if not ObjectId.is_valid(role_id):
                    errors.append(f'ID invalide pour le rôle: {role_data.get("nom", "Inconnu")}')
                    continue
                
                # Mettre à jour le rôle
                update_data = {
                    'updated_at': datetime.utcnow()
                }
                
                allowed_fields = ['nom', 'description', 'couleur', 'ordre', 'permissions']
                for field in allowed_fields:
                    if field in role_data:
                        update_data[field] = role_data[field]
                
                result = roles_collection.update_one(
                    {'_id': ObjectId(role_id)},
                    {'$set': update_data}
                )
                
                if result.modified_count > 0:
                    updated_count += 1
                    
            except Exception as e:
                errors.append(f'Erreur pour le rôle {role_data.get("nom", "Inconnu")}: {str(e)}')
        
        return jsonify({
            'message': f'Mise à jour terminée: {updated_count} rôles mis à jour',
            'updated_count': updated_count,
            'errors': errors
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la mise à jour en lot',
            'error': str(e)
        }), 500

@app.route("/api/permissions/categories", methods=["GET"])
@token_required
def get_permission_categories(current_user_id):
    """Récupérer toutes les catégories de permissions"""
    try:
        categories = permissions_collection.distinct('category')
        return jsonify({
            'message': 'Catégories récupérées avec succès',
            'data': sorted(categories)
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de la récupération des catégories',
            'error': str(e)
        }), 500

@app.route("/api/roles/export", methods=["GET"])
@token_required
@permission_required('roles_manage')
def export_roles_and_permissions(current_user_id):
    """Exporter tous les rôles et permissions (admin seulement)"""
    try:
        # Récupérer tous les rôles
        roles = list(roles_collection.find().sort("ordre", 1))
        for role in roles:
            role['_id'] = str(role['_id'])
        
        # Récupérer toutes les permissions
        permissions = list(permissions_collection.find().sort("category", 1))
        for permission in permissions:
            permission['_id'] = str(permission['_id'])
        
        return jsonify({
            'message': 'Export réussi',
            'data': {
                'roles': roles,
                'permissions': permissions,
                'exported_at': datetime.utcnow().isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de l\'export',
            'error': str(e)
        }), 500

@app.route("/api/roles/import", methods=["POST"])
@token_required
@permission_required('roles_manage')
def import_roles_and_permissions(current_user_id):
    """Importer des rôles et permissions (admin seulement)"""
    try:
        data = request.get_json()
        
        if 'roles' not in data and 'permissions' not in data:
            return jsonify({'message': 'Données d\'import invalides'}), 400
        
        imported_roles = 0
        imported_permissions = 0
        errors = []
        
        # Importer les permissions
        if 'permissions' in data:
            for perm_data in data['permissions']:
                try:
                    # Vérifier si la permission existe déjà
                    existing = permissions_collection.find_one({'nom': perm_data['nom']})
                    if not existing:
                        perm_data['created_at'] = datetime.utcnow()
                        permissions_collection.insert_one(perm_data)
                        imported_permissions += 1
                except Exception as e:
                    errors.append(f'Erreur permission {perm_data.get("nom", "Inconnu")}: {str(e)}')
        
        # Importer les rôles
        if 'roles' in data:
            for role_data in data['roles']:
                try:
                    # Vérifier si le rôle existe déjà
                    existing = roles_collection.find_one({'nom': role_data['nom']})
                    if not existing:
                        role_data['created_at'] = datetime.utcnow()
                        role_data['updated_at'] = datetime.utcnow()
                        roles_collection.insert_one(role_data)
                        imported_roles += 1
                except Exception as e:
                    errors.append(f'Erreur rôle {role_data.get("nom", "Inconnu")}: {str(e)}')
        
        return jsonify({
            'message': f'Import terminé: {imported_roles} rôles, {imported_permissions} permissions importés',
            'imported_roles': imported_roles,
            'imported_permissions': imported_permissions,
            'errors': errors
        }), 200
    except Exception as e:
        return jsonify({
            'message': 'Erreur lors de l\'import',
            'error': str(e)
        }), 500


@app.route("/")
def home():
    return render_template('index.html')

@app.route("/admin")
def admin():
    return render_template('admin.html')

@app.route("/login")
def login_page():
    return render_template('login.html')

# ===========================================
# FONCTIONS DE VALIDATION
# ===========================================

def validate_email(email):
    """Valider le format de l'email"""
    if not email or not isinstance(email, str):
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Valider le mot de passe (minimum 6 caractères)"""
    return password and isinstance(password, str) and len(password) >= 6

def validate_telephone(telephone):
    """Valider le format du téléphone"""
    if not telephone:
        return True  # Optionnel
    if not isinstance(telephone, str):
        return False
    # Format international simple
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, telephone) is not None

def validate_statut(statut):
    """Valider le statut utilisateur"""
    if not statut:
        return True  # Optionnel
    valid_statuts = ["actif", "inactif"]
    return statut in valid_statuts

def validate_user_fonction(fonction):
    """Valider la fonction de l'utilisateur"""
    return True  # Accepter toutes les fonctions

def validate_gerer(gerer):
    """Valider le champ gerer (boolean)"""
    return isinstance(gerer, bool)

def validate_panier_title(title):
    """Valider le titre du panier"""
    return title and isinstance(title, str) and len(title.strip()) > 0

# def validate_panier_type(type_field):
#     """Valider le type du panier"""
#     valid_types = ["appel_offre", "consultation", "marché", "prestation"]
#     return type_field in valid_types

# def validate_panier_price(price):
#     """Valider le prix du panier"""
#     try:
#         price_float = float(price)
#         return price_float >= 0
#     except (ValueError, TypeError):
#         return False

# def validate_panier_status(status):
#     """Valider le statut du panier"""
#     valid_statuses = ["Non préparé", "En préparation", "Envoyée"]
#     return status in valid_statuses

def validate_panier_deadline(deadline):
    """Valider la date limite"""
    if not deadline:
        return True  # Optionnel
    try:
        datetime.fromisoformat(deadline.replace('Z', '+00:00'))
        return True
    except (ValueError, TypeError):
        return False

def validate_panier_source(source):
    """Valider l'URL source"""
    if not source:
        return True  # Optionnel
    pattern = r'^https?://.+'
    return re.match(pattern, source) is not None

def validate_panier_note(note):
    """Valider les notes (liste d'URLs)"""
    if not note:
        return True  # Optionnel
    if not isinstance(note, list):
        return False
    pattern = r'^https?://.+'
    return all(re.match(pattern, url) for url in note if url)

def validate_panier_commentaire(commentaire):
    """Valider le commentaire"""
    return isinstance(commentaire, str)

def validate_raison_sociale(raison_sociale):
    """Valider la raison sociale"""
    return raison_sociale and isinstance(raison_sociale, str) and len(raison_sociale.strip()) > 0

def validate_nom_prenom(nom_prenom):
    """Valider le nom et prénom"""
    return nom_prenom and isinstance(nom_prenom, str) and len(nom_prenom.strip()) > 0

def validate_whatsapp(whatsapp):
    """Valider le numéro WhatsApp"""
    if not whatsapp:
        return True  # Optionnel
    if not isinstance(whatsapp, str):
        return False
    # Format international simple
    pattern = r'^\+?[1-9]\d{1,14}$'
    return re.match(pattern, whatsapp) is not None

def validate_adresse(adresse):
    """Valider l'adresse"""
    if not adresse:
        return True  # Optionnel
    return isinstance(adresse, str)

def validate_note_commentaire(note_commentaire):
    """Valider la note/commentaire"""
    if not note_commentaire:
        return True  # Optionnel
    return isinstance(note_commentaire, str)

# ===========================================
# VALIDATIONS POUR LES OFFRES
# ===========================================

def validate_offre_intitulee(intitulee):
    """Valider l'intitulé de l'offre"""
    return isinstance(intitulee, str) and len(intitulee.strip()) > 0

def validate_offre_lien(lien):
    """Valider le lien de l'offre"""
    if not isinstance(lien, str):
        return False
    return len(lien.strip()) > 0

def validate_offre_client(client):
    """Valider le client de l'offre"""
    return isinstance(client, str) and len(client.strip()) > 0

def validate_offre_date_limite(date_limite):
    """Valider la date limite de l'offre"""
    if not isinstance(date_limite, str):
        return False
    try:
        from datetime import datetime
        datetime.fromisoformat(date_limite.replace('Z', '+00:00'))
        return True
    except:
        return False

# def validate_offre_statut(statut):
#     """Valider le statut de l'offre"""
#     return statut in ["Non préparé", "En préparation", "Envoyée"]

def validate_offre_responsable_id(responsable_id):
    """Valider l'ID du responsable"""
    if not isinstance(responsable_id, str):
        return False
    try:
        ObjectId(responsable_id)
        return True
    except:
        return False

def validate_offre_categorie(categorie):
    """Valider la catégorie de l'offre"""
    if not categorie:
        return True  # Optionnel
    valid_categories = ["nationale", "internationale"]
    return isinstance(categorie, str) and categorie.lower() in valid_categories

def validate_offre_numero(numero):
    """Valider le numéro d'offre (N-Offre)"""
    if not numero:
        return True  # Optionnel
    return isinstance(numero, str) and len(numero.strip()) > 0

def validate_offre_partenaire(partenaire):
    """Valider le partenaire de l'offre"""
    if not partenaire:
        return True  # Optionnel
    return isinstance(partenaire, str) and len(partenaire.strip()) > 0

def validate_offre_documents(documents):
    """Valider les documents de l'offre"""
    if not isinstance(documents, list):
        return False
    
    # Accepter les strings (URLs) ou les objets de fichiers
    for doc in documents:
        if isinstance(doc, str):
            continue  # URL ou chemin de fichier
        elif isinstance(doc, dict) and 'filename' in doc:
            continue  # Objet fichier uploadé
        elif hasattr(doc, 'filename'):
            continue  # Objet File Flask
        else:
            return False
    
    return True

def validate_documents_array(documents):
    """Valider un array de documents (URLs) pour devis/factures"""
    if not documents:
        return True  # Optionnel
    
    if not isinstance(documents, list):
        return False
    
    # Vérifier que chaque élément est une string (URL) valide
    for doc in documents:
        if not isinstance(doc, str) or not doc.strip():
            return False
    
    return True

def upload_document_to_cloudinary(file, folder="offres_documents"):
    """Upload un document vers Cloudinary et retourne l'URL"""
    try:
        import cloudinary
        import cloudinary.uploader
        
        # Configuration Cloudinary (utilise les mêmes credentials que t.py)
        cloudinary.config(
            cloud_name="dskdortsz",  
            api_key="843918322767789",          
            api_secret="CEgn2u-KoQyfCFmiGcv48125tYc"
        )
        
        # Déterminer le type de ressource basé sur l'extension
        filename = file.filename.lower()
        if filename.endswith(('.pdf', '.doc', '.docx', '.txt')):
            resource_type = "raw"
        elif filename.endswith(('.jpg', '.jpeg', '.png', '.gif')):
            resource_type = "image"
        else:
            resource_type = "raw"
        
        # Upload vers Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type=resource_type,
            access_mode="public",
            use_filename=True,
            unique_filename=False
        )
        
        return result['secure_url']
    except Exception as e:
        print(f"Erreur upload Cloudinary: {str(e)}")
        return None

def viewer_required(f):
    """Décorateur pour vérifier que l'utilisateur est au moins spectateur (peut voir mais pas modifier)"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"message": "Token manquant"}), 401
        try:
            token = auth.split(" ")[1]
            decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            role = decoded.get("role")
            if role not in ["admin", "user", "spectateur", "TEST"]:
                return jsonify({"message": "Accès refusé - Rôle insuffisant"}), 403
            request.current_user = decoded
        except:
            return jsonify({"message": "Token invalide"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/api/sources", methods=["GET"])
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


@app.route("/api/recherche", methods=["GET"])
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


@app.route("/api/sources/grouped", methods=["GET"])
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

    # Debug: afficher les catégories existantes
    all_categories = sources_col.distinct("categorie")
    print(f"Catégories trouvées dans la base: {all_categories}")

    return jsonify({
        "nationale": fetch_block("Nationale"),
        "internationale": fetch_block("Internationale"),
        "debug_categories": all_categories  # Pour debug
    })    
# Routes Auth
@app.route("/register", methods=["POST"])
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
    print(f"DEBUG: Validation du rôle '{role}' - Trouvé: {existing_role is not None}")
    if not existing_role:
        return jsonify({"message": f"Rôle '{role}' n'existe pas dans la base de données"}), 400

    if users_col.find_one({"email": email}):
        return jsonify({"message": "Utilisateur déjà existant"}), 400

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

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"message": "Utilisateur non trouvé"}), 404

    if bcrypt.check_password_hash(user["password"], password):
        # Token valide pour 30 jours (peut être changé selon vos besoins)
        token = jwt.encode({
            "user_id": str(user["_id"]),
            "role": user.get("role", "user"),
            "exp": datetime.utcnow() + timedelta(days=30)  # 30 jours au lieu de 7
        }, app.config["SECRET_KEY"], algorithm="HS256")
        return jsonify({
            "token": token, 
            "user_id": str(user["_id"]),
            "role": user.get("role", "user"), 
            "name": user.get("name"),
            "email": user.get("email"),
            "telephone": user.get("telephone", ""),
            "whatsapp": user.get("whatsapp", ""),
            "adresse": user.get("adresse", ""),
            "statut": user.get("statut", "actif")
        })
    else:
        return jsonify({"message": "Mot de passe incorrect"}), 401

# Ajouter source (admin)


@app.route("/api/sources", methods=["POST"])
@token_required
@permission_required('sources_create')
def add_source(current_user_id):
    data = request.get_json()
    if not all([data.get("nom_entite"), data.get("url"), data.get("categorie")]):
        return jsonify({"message": "Champs manquants"}), 400
    
    # Réorganiser les ordres AVANT l'insertion
    new_order = data.get("order", 1)
    categorie = data.get("categorie")
    if new_order and categorie:
        reorganize_orders_on_insert(categorie, new_order)
    
    sources_col.insert_one(data)
    return jsonify({"message": "Source ajoutée"}), 201

# Fonctions pour réorganiser les ordres
def reorganize_orders_on_update(categorie, old_order, new_order, entity_id):
    """Réorganise les ordres lors de la modification"""
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
    print(f"DEBUG: Réorganisation insertion - Catégorie: '{categorie}', Nouvel ordre: {new_order}")
    
    # Compter les éléments qui seront affectés
    count_before = sources_col.count_documents({
        "categorie": categorie,
        "order": {"$gte": new_order}
    })
    print(f"DEBUG: {count_before} éléments seront décalés dans la catégorie '{categorie}'")
    
    result = sources_col.update_many(
        {
            "categorie": categorie,
            "order": {"$gte": new_order}
        },
        {"$inc": {"order": 1}}
    )
    
    print(f"DEBUG: {result.modified_count} éléments modifiés")

# Route PUT complète avec vérification auth
@app.route("/api/sources/<source_id>", methods=["PUT"])
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
    
    old_order = old_entity.get("order", 0)
    new_order = data.get("order", old_order)
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
    
    # Mettre à jour l'entité
    sources_col.update_one(
        {"_id": ObjectId(source_id)},
        {"$set": data}
    )
    return jsonify({"message": "Source mise à jour"}), 200
# Routes pour modification et suppression
# @app.route("/api/sources/<source_id>", methods=["PUT"])
# def update_source(source_id):
#     auth = request.headers.get("Authorization")
#     if not auth:
#         return jsonify({"message": "Token manquant"}), 401
#     try:
#         token = auth.split(" ")[1]
#         decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
#     except:
#         return jsonify({"message": "Token invalide"}), 401
#     if decoded.get("role") != "admin":
#         return jsonify({"message": "Accès refusé"}), 403

#     data = request.get_json()
#     if not all([data.get("nom_entite"), data.get("url"), data.get("categorie")]):
#         return jsonify({"message": "Champs manquants"}), 400
    
#     sources_col.update_one(
#         {"_id": ObjectId(source_id)},
#         {"$set": data}
#     )
#     return jsonify({"message": "Source mise à jour"}), 200

@app.route("/api/sources/<source_id>", methods=["DELETE"])
@token_required
@permission_required('sources_delete')
def delete_source(current_user_id, source_id):
    sources_col.delete_one({"_id": ObjectId(source_id)})
    return jsonify({"message": "Source supprimée"}), 200


# ===========================================
# GESTION DES UTILISATEURS (ADMIN) - ROUTES MANQUANTES
# ===========================================

def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if not auth:
            return jsonify({"message": "Token manquant"}), 401
        try:
            token = auth.split(" ")[1]
            decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
            if decoded.get("role") != "admin":
                return jsonify({"message": "Accès refusé - Admin requis"}), 403
        except:
            return jsonify({"message": "Token invalide"}), 401
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def optional_auth(f):
    """Décorateur pour authentification optionnelle (pour Railway)"""
    def decorated_function(*args, **kwargs):
        auth = request.headers.get("Authorization")
        if auth:
            try:
                token = auth.split(" ")[1]
                decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
                request.current_user = decoded
            except:
                request.current_user = None
        else:
            request.current_user = None
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@app.route("/api/users", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_users(current_user_id):
    """Récupérer tous les utilisateurs"""
    try:
        # Vérifier la connexion à la base de données
        client.admin.command('ping')
        
        # Récupérer les utilisateurs
        users = list(users_col.find({}, {"password": 0}).sort("email", 1))
        
        # Convertir les ObjectId en string
        for user in users:
            user["_id"] = str(user["_id"])
        
        print(f"DEBUG: Récupéré {len(users)} utilisateurs depuis la base de données")
        return jsonify(users), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des utilisateurs: {str(e)}")
        return jsonify({"message": f"Erreur lors de la récupération des utilisateurs: {str(e)}"}), 500

@app.route("/api/users", methods=["POST"])
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
        # Hasher le mot de passe
        hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
        
        # Créer l'utilisateur
        user = {
            "name": data["name"],
            "email": data["email"],
            "password": hashed_password,
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

@app.route("/api/users/<user_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération de l'utilisateur: {str(e)}"}), 500
        
@app.route("/api/users/<user_id>/with-password", methods=["GET"])
@token_required
@permission_required('users_manage')
def get_user_with_password(current_user_id, user_id):
    """Récupérer un utilisateur spécifique avec son mot de passe (admin uniquement)"""
    try:
        # Récupérer l'utilisateur AVEC le mot de passe
        user = users_col.find_one({"_id": ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Convertir l'ObjectId en string
        user["_id"] = str(user["_id"])
        
        # Retourner l'utilisateur avec le mot de passe
        return jsonify(user), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/<user_id>", methods=["PUT"])
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
            # Hacher le nouveau mot de passe
            hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
            update_data["password"] = hashed_password
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
        return jsonify({"message": f"Erreur lors de la mise à jour de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/<user_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression de l'utilisateur: {str(e)}"}), 500

@app.route("/api/users/stats", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération des statistiques: {str(e)}"}), 500

@app.route("/api/users/<user_id>/change-password", methods=["POST"])
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

@app.route("/api/admin/change-password", methods=["POST"])
@token_required
@permission_required('users_manage')
def admin_change_own_password(current_user_id):
    """Changer son propre mot de passe (admin uniquement)"""
    auth = request.headers.get("Authorization")
    if not auth:
        return jsonify({"message": "Token manquant"}), 401
    
    try:
        token = auth.split(" ")[1]
        decoded = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except:
        return jsonify({"message": "Token invalide"}), 401
    
    if decoded.get("role") != "admin":
        return jsonify({"message": "Accès refusé"}), 403
    
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
        # Récupérer l'utilisateur admin
        user = users_col.find_one({"_id": ObjectId(decoded.get("user_id"))})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        # Vérifier le mot de passe actuel
        if not bcrypt.check_password_hash(user["password"], data["current_password"]):
            return jsonify({"message": "Mot de passe actuel incorrect"}), 400
        
        # Hasher le nouveau mot de passe
        new_hashed_password = bcrypt.generate_password_hash(data["new_password"]).decode("utf-8")
        
        # Mettre à jour le mot de passe
        users_col.update_one(
            {"_id": ObjectId(decoded.get("user_id"))},
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

# ===========================================
# ROUTES DE TEST
# ===========================================


# @app.route("/api/users-public", methods=["GET"])
# def get_users_public():
#     """Route publique pour tester (TEMPORAIRE - À SUPPRIMER EN PRODUCTION)"""
#     try:
#         users = list(users_col.find({}, {"password": 0}).sort("email", 1))
#         for user in users:
#             user["_id"] = str(user["_id"])
#         return jsonify({"users": users, "count": len(users)})
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

# @app.route("/api/debug", methods=["GET"])
# def debug_info():
#     """Route de diagnostic pour Railway"""
#     try:
#         # Test de connexion MongoDB
#         client.admin.command('ping')
#         mongo_status = "Connected"
#     except Exception as e:
#         mongo_status = f"Error: {str(e)}"
    
#     try:
#         # Compter les utilisateurs
#         user_count = users_col.count_documents({})
#         users_status = f"Found {user_count} users"
#     except Exception as e:
#         users_status = f"Error: {str(e)}"
    
#     try:
#         # Compter les sources
#         sources_count = sources_col.count_documents({})
#         sources_status = f"Found {sources_count} sources"
#     except Exception as e:
#         sources_status = f"Error: {str(e)}"
    
#     return jsonify({
#         "status": "Debug Info",
#         "mongo_uri": MONGO_URI[:50] + "..." if len(MONGO_URI) > 50 else MONGO_URI,
#         "mongo_status": mongo_status,
#         "users_status": users_status,
#         "sources_status": sources_status,
#         "jwt_secret_set": bool(app.config["SECRET_KEY"]),
#         "environment": {
#             "PORT": os.getenv("PORT", "Not set"),
#             "JWT_SECRET": "Set" if os.getenv("JWT_SECRET") else "Not set",
#             "MONGO_URI": "Set" if os.getenv("MONGO_URI") else "Not set"
#         }
#     })

@app.route("/api/test-jwt", methods=["GET"])
def test_jwt():
    """Test de la configuration JWT"""
    try:
        # Test de génération de token
        test_token = jwt.encode({
            "test": "value",
            "exp": datetime.utcnow() + timedelta(minutes=1)
        }, app.config["SECRET_KEY"], algorithm="HS256")
        
        # Test de décodage
        decoded = jwt.decode(test_token, app.config["SECRET_KEY"], algorithms=["HS256"])
        
        return jsonify({
            "status": "JWT OK",
            "secret_key_set": bool(app.config["SECRET_KEY"]),
            "test_decoded": decoded
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# ===========================================
# GESTION DES CLIENTS
# ===========================================

@app.route("/api/clients", methods=["GET"])
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
        print(f"ERROR: Erreur lors de la récupération des clients: {str(e)}")
        return jsonify([]), 200

@app.route("/api/clients", methods=["POST"])
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
        return jsonify({"message": f"Erreur lors de la création du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["PUT"])
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
        return jsonify({"message": f"Erreur lors de la mise à jour du client: {str(e)}"}), 500

@app.route("/api/clients/<client_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression du client: {str(e)}"}), 500

# ===========================================
# GESTION DES PARTENAIRES
# ===========================================

@app.route("/api/partenaires", methods=["GET"])
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
        print(f"ERROR: Erreur lors de la récupération des partenaires: {str(e)}")
        return jsonify([]), 200

@app.route("/api/partenaires", methods=["POST"])
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
        return jsonify({"message": f"Erreur lors de la création du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["PUT"])
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
        return jsonify({"message": f"Erreur lors de la mise à jour du partenaire: {str(e)}"}), 500

@app.route("/api/partenaires/<partenaire_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression du partenaire: {str(e)}"}), 500

# ===========================================
# GESTION DES PERSONNELS
# ===========================================

@app.route("/api/personnels", methods=["GET"])
@token_required
@permission_required('personnel_view')
def get_personnels(current_user_id):
    """Récupérer tous les personnels"""
    try:
        personnels = list(personnels_col.find().sort("nom_prenom", 1))
        
        for personnel in personnels:
            personnel["_id"] = str(personnel["_id"])
        
        return jsonify(personnels), 200
    except Exception as e:
        print(f"ERROR: Erreur lors de la récupération des personnels: {str(e)}")
        return jsonify([]), 200

@app.route("/api/personnels", methods=["POST"])
@token_required
@permission_required('personnel_manage')
def create_personnel(current_user_id):
    """Créer un nouveau personnel (admin uniquement)"""
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
        note_commentaire = data.get("note_commentaire", "")
        
        if whatsapp and not validate_whatsapp(whatsapp):
            return jsonify({"message": "Format de WhatsApp invalide"}), 400
        if adresse and not validate_adresse(adresse):
            return jsonify({"message": "Format d'adresse invalide"}), 400
        if note_commentaire and not validate_note_commentaire(note_commentaire):
            return jsonify({"message": "Format de note/commentaire invalide"}), 400
        
        # Vérifier si l'email existe déjà
        if personnels_col.find_one({"email": data["email"]}):
            return jsonify({"message": "Un personnel avec cet email existe déjà"}), 400
        
        # Créer le personnel
        personnel = {
            "nom_prenom": data["nom_prenom"],
            "telephone": data["telephone"],
            "whatsapp": whatsapp,
            "email": data["email"],
            "adresse": adresse,
            "note_commentaire": note_commentaire,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = personnels_col.insert_one(personnel)
        personnel["_id"] = str(result.inserted_id)
        
        return jsonify({"message": "Personnel créé avec succès", "personnel": personnel}), 201
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la création du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["GET"])
@token_required
@permission_required('personnel_view')
def get_personnel(current_user_id, personnel_id):
    """Récupérer un personnel spécifique"""
    try:
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Personnel non trouvé"}), 404
        
        personnel["_id"] = str(personnel["_id"])
        return jsonify(personnel), 200
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la récupération du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["PUT"])
@token_required
@permission_required('personnel_manage')
def update_personnel(current_user_id, personnel_id):
    """Modifier un personnel (admin uniquement)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        # Vérifier que le personnel existe
        personnel = personnels_col.find_one({"_id": ObjectId(personnel_id)})
        if not personnel:
            return jsonify({"message": "Personnel non trouvé"}), 404
        
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
            # Vérifier que l'email n'est pas déjà utilisé par un autre personnel
            existing_personnel = personnels_col.find_one({"email": data["email"], "_id": {"$ne": ObjectId(personnel_id)}})
            if existing_personnel:
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
        
        # Mettre à jour le personnel
        result = personnels_col.update_one(
            {"_id": ObjectId(personnel_id)},
            {"$set": update_data}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Personnel mis à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour du personnel: {str(e)}"}), 500

@app.route("/api/personnels/<personnel_id>", methods=["DELETE"])
@token_required
@permission_required('personnel_manage')
def delete_personnel(current_user_id, personnel_id):
    """Supprimer un personnel (admin uniquement)"""
    try:
        result = personnels_col.delete_one({"_id": ObjectId(personnel_id)})
        
        if result.deleted_count > 0:
            return jsonify({"message": "Personnel supprimé avec succès"}), 200
        else:
            return jsonify({"message": "Personnel non trouvé"}), 404
            
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la suppression du personnel: {str(e)}"}), 500

# ===========================================
# ROUTES DE DEBUG POUR RAILWAY
# ===========================================

@app.route("/api/debug", methods=["GET"])
def debug_info():
    """Route de diagnostic pour Railway"""
    try:
        # Test de connexion MongoDB
        client.admin.command('ping')
        mongo_status = "Connected"
    except Exception as e:
        mongo_status = f"Error: {str(e)}"
    
    try:
        # Compter les utilisateurs
        user_count = users_col.count_documents({})
        users_status = f"Found {user_count} users"
    except Exception as e:
        users_status = f"Error: {str(e)}"
    
    try:
        # Compter les sources
        sources_count = sources_col.count_documents({})
        sources_status = f"Found {sources_count} sources"
    except Exception as e:
        sources_status = f"Error: {str(e)}"
    
    return jsonify({
        "status": "Debug Info",
        "mongo_uri": MONGO_URI[:50] + "..." if len(MONGO_URI) > 50 else MONGO_URI,
        "mongo_status": mongo_status,
        "users_status": users_status,
        "sources_status": sources_status,
        "jwt_secret_set": bool(app.config["SECRET_KEY"]),
        "environment": {
            "PORT": os.getenv("PORT", "Not set"),
            "JWT_SECRET": "Set" if os.getenv("JWT_SECRET") else "Not set",
            "MONGO_URI": "Set" if os.getenv("MONGO_URI") else "Not set"
        }
    })

# ===========================================
# GESTION DES OFFRES
# ===========================================

@app.route("/api/offres", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_offres(current_user_id):
    """Récupérer toutes les offres (admin voit tout, utilisateur voit ses offres)"""
    try:
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
        # Construire la requête selon les permissions
        query = {}
        
        # Vérifier les permissions pour le filtrage
        if user_role == "user" or user_role == "spectateur":
            # Les utilisateurs simples ne voient que leurs offres
            if user_id:
                query["responsable_id"] = ObjectId(user_id)
            else:
                # Si pas d'ID utilisateur, retourner une liste vide
                return jsonify([]), 200
        # Les admins voient toutes les offres (pas de filtrage)
        
        print(f"DEBUG: Récupération des offres - user_role: {user_role}, user_id: {user_id}")
        print(f"DEBUG: Query utilisée: {query}")
        
        offres = list(offres_col.find(query).sort("updated_at", -1))
        
        print(f"DEBUG: Nombre d'offres trouvées: {len(offres)}")
        
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
        print(f"ERROR: Erreur lors de la récupération des offres: {str(e)}")
        return jsonify([]), 200

@app.route("/api/offres", methods=["POST"])
@token_required
@permission_required('devis_create')
def add_offre(current_user_id):
    """Ajouter une offre"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        print(f"DEBUG: Données reçues pour création d'offre: {data}")
        print(f"DEBUG: current_user_id depuis décorateur: {current_user_id}")
        
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
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
        # # Validation du statut (commenté car géré dynamiquement en frontend)
        # if "statut" in data and not validate_offre_statut(data["statut"]):
        #     return jsonify({"message": "Statut invalide. Doit être: Non préparé, En préparation, ou Envoyée"}), 400
        
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
        from datetime import datetime
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
        
        print(f"DEBUG: Création d'offre avec données: {offre}")
        
        result = offres_col.insert_one(offre)
        offre["_id"] = str(result.inserted_id)
        offre["responsable_id"] = str(offre["responsable_id"])
        
        return jsonify({"message": "Offre créée avec succès", "offre": offre}), 201
        
    except Exception as e:
        print(f"ERROR: Erreur lors de la création de l'offre: {str(e)}")
        return jsonify({"message": f"Erreur lors de la création de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["PUT"])
@token_required
@permission_required('devis_edit')
def update_offre(current_user_id, offre_id):
    """Modifier une offre"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        print(f"DEBUG: Données reçues pour modification d'offre {offre_id}: {data}")
        print(f"DEBUG: Clés présentes dans data: {list(data.keys())}")
        
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
            # # Validation du statut (commenté car géré dynamiquement en frontend)
            # if not validate_offre_statut(data["statut"]):
            #     return jsonify({"message": "Statut invalide. Doit être: Non préparé, En préparation, ou Envoyée"}), 400
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
        print(f"DEBUG: Vérification des nouveaux champs...")
        print(f"DEBUG: 'Catégorie' in data: {'Catégorie' in data}")
        print(f"DEBUG: 'N-Offre' in data: {'N-Offre' in data}")
        print(f"DEBUG: 'Partenaire' in data: {'Partenaire' in data}")
        
        # Toujours mettre à jour les nouveaux champs, même s'ils sont vides
        if "Catégorie" in data:
            print(f"DEBUG: Catégorie trouvée: '{data['Catégorie']}'")
            if not validate_offre_categorie(data["Catégorie"]):
                return jsonify({"message": "Catégorie invalide. Doit être: nationale, internationale"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["Catégorie"] = data["Catégorie"]  # Nom original
            update_data["categorie"] = data["Catégorie"]  # Nom mappé
            print(f"DEBUG: Catégorie ajoutée à update_data: '{data['Catégorie']}'")
        
        if "N-Offre" in data:
            print(f"DEBUG: N-Offre trouvé: '{data['N-Offre']}'")
            if not validate_offre_numero(data["N-Offre"]):
                return jsonify({"message": "Numéro d'offre invalide"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["N-Offre"] = data["N-Offre"]  # Nom original
            update_data["numero"] = data["N-Offre"]  # Nom mappé
            print(f"DEBUG: N-Offre ajouté à update_data: '{data['N-Offre']}'")
        
        if "Partenaire" in data:
            print(f"DEBUG: Partenaire trouvé: '{data['Partenaire']}'")
            if not validate_offre_partenaire(data["Partenaire"]):
                return jsonify({"message": "Partenaire invalide"}), 400
            # Mettre à jour avec les deux noms pour compatibilité
            update_data["Partenaire"] = data["Partenaire"]  # Nom original
            update_data["partenaire"] = data["Partenaire"]  # Nom mappé
            print(f"DEBUG: Partenaire ajouté à update_data: '{data['Partenaire']}'")
        
        print(f"DEBUG: Données de mise à jour préparées: {update_data}")
        
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
        
        print(f"DEBUG: Résultat de la mise à jour - modified_count: {result.modified_count}")
        
        if result.modified_count > 0:
            return jsonify({"message": "Offre mise à jour avec succès"}), 200
        else:
            return jsonify({"message": "Aucune modification effectuée"}), 200
        
    except Exception as e:
        return jsonify({"message": f"Erreur lors de la mise à jour de l'offre: {str(e)}"}), 500

@app.route("/api/offres/<offre_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression de l'offre: {str(e)}"}), 500

@app.route("/api/offres/stats", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_offres_stats(current_user_id):
    """Statistiques des offres"""
    try:
        # Récupérer l'utilisateur actuel
        current_user = getattr(request, 'current_user', None)
        user_id = current_user.get('user_id') if current_user else None
        user_role = current_user.get('role') if current_user else None
        
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
        print(f"ERROR: Erreur lors de la récupération des statistiques: {str(e)}")
        return jsonify({
            "total_offres": 0,
            "non_prepare_offres": 0,
            "en_preparation_offres": 0,
            "envoyee_offres": 0
        }), 200

@app.route("/api/test-offres", methods=["GET"])
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
        return jsonify({
            "status": "Offres Error",
            "message": f"Erreur de connexion à la collection offres: {str(e)}"
        }), 500

@app.route("/api/test-update-offre/<offre_id>", methods=["PUT"])
def test_update_offre(offre_id):
    """Test de mise à jour d'offre avec les nouveaux champs"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        print(f"DEBUG TEST: Mise à jour de l'offre {offre_id} avec: {data}")
        
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
        
        print(f"DEBUG TEST: Données de mise à jour: {update_data}")
        
        # Mettre à jour l'offre
        result = offres_col.update_one(
            {"_id": ObjectId(offre_id)},
            {"$set": update_data}
        )
        
        print(f"DEBUG TEST: Résultat - modified_count: {result.modified_count}")
        
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
        return jsonify({
            "message": f"Erreur lors du test de mise à jour: {str(e)}"
        }), 500
        
# ===========================================
# GESTION DES DEVIS
# ===========================================

@app.route("/api/devis", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_devis(current_user_id):
    """Récupérer tous les devis (admin voit tout, utilisateur voit ses devis)"""
    try:
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
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
        print(f"ERROR: Erreur lors de la récupération des devis: {str(e)}")
        return jsonify([]), 200

@app.route("/api/devis", methods=["POST"])
@token_required
@permission_required('devis_create')
def create_devis(current_user_id):
    """Créer un nouveau devis"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        print(f"DEBUG: current_user_id depuis décorateur: {current_user_id}")
        
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
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
        
        # # Vérifier l'état (commenté car géré dynamiquement en frontend)
        # valid_etats = ["Validé", "Transformé en facture"]
        # if data["etat"] not in valid_etats:
        #     return jsonify({"message": "État invalide. Doit être: Validé, Transformé en facture"}), 400
        
        # Vérifier que l'offre existe et récupérer ses données
        offre = offres_col.find_one({"_id": ObjectId(data["offre_id"])})
        if not offre:
            return jsonify({"message": "Offre non trouvée"}), 400
        
        # Vérifier que le client existe et récupérer ses données
        client = clients_col.find_one({"_id": ObjectId(data["client_id"])})
        if not client:
            return jsonify({"message": "Client non trouvé"}), 400
        
        # # Générer le numéro de devis automatiquement avec les noms
        # nom_client = client.get("nom", "Client").replace(" ", "_")
        # nom_offre = offre.get("titre", "Offre").replace(" ", "_")
        # numero_devis = f"Dev_{nom_client}_{nom_offre}"
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
        print(f"ERROR: Erreur lors de la création du devis: {str(e)}")
        return jsonify({"message": f"Erreur lors de la création du devis: {str(e)}"}), 500

@app.route("/api/devis/<devis_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération du devis: {str(e)}"}), 500

@app.route("/api/devis/<devis_id>", methods=["PUT"])
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
            # # Validation de l'état (commenté car géré dynamiquement en frontend)
            # valid_etats = ["Validé", "Transformé en facture"]
            # if data["etat"] not in valid_etats:
            #     return jsonify({"message": "État invalide. Doit être: Validé, Transformé en facture"}), 400
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
        return jsonify({"message": f"Erreur lors de la mise à jour du devis: {str(e)}"}), 500

@app.route("/api/devis/<devis_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression du devis: {str(e)}"}), 500

# ===========================================
# GESTION DES FACTURES
# ===========================================

@app.route("/api/factures", methods=["GET"])
@token_required
@permission_required('factures_view')
def get_factures(current_user_id):
    """Récupérer toutes les factures (admin voit tout, utilisateur voit ses factures)"""
    try:
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
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
        print(f"ERROR: Erreur lors de la récupération des factures: {str(e)}")
        return jsonify([]), 200

@app.route("/api/factures", methods=["POST"])
@token_required
@permission_required('factures_create')
def create_facture(current_user_id):
    """Créer une nouvelle facture"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"message": "Données manquantes"}), 400
        
        print(f"DEBUG: current_user_id depuis décorateur: {current_user_id}")
        
        # L'utilisateur actuel est déjà fourni par @token_required
        user_id = current_user_id
        
        # Récupérer le rôle depuis la base
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get('role')
        
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
        
        # # Vérifier l'état
        # valid_etats = ["A envoyer au client", "En attente de payement", "Payée"]
        # if data["etat"] not in valid_etats:
        #     return jsonify({"message": "État invalide. Doit être: A envoyer au client, En attente de payement, Payée"}), 400
        
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
        
        # # Générer le numéro de facture automatiquement avec les noms
        # nom_client = client.get("nom", "Client").replace(" ", "_")
        # nom_offre = offre.get("titre", "Offre").replace(" ", "_")
        # numero_facture = f"Fac_{nom_client}_{nom_offre}"
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
        print(f"ERROR: Erreur lors de la création de la facture: {str(e)}")
        return jsonify({"message": f"Erreur lors de la création de la facture: {str(e)}"}), 500

@app.route("/api/factures/<facture_id>", methods=["GET"])
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
        return jsonify({"message": f"Erreur lors de la récupération de la facture: {str(e)}"}), 500

@app.route("/api/factures/<facture_id>", methods=["PUT"])
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
            # # Validation de l'état (commenté car géré dynamiquement en frontend)
            # valid_etats = ["A envoyer au client", "En attente de payement", "Payée"]
            # if data["etat"] not in valid_etats:
            #     return jsonify({"message": "État invalide. Doit être: A envoyer au client, En attente de payement, Payée"}), 400
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
        return jsonify({"message": f"Erreur lors de la mise à jour de la facture: {str(e)}"}), 500

@app.route("/api/factures/<facture_id>", methods=["DELETE"])
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
        return jsonify({"message": f"Erreur lors de la suppression de la facture: {str(e)}"}), 500

# ===========================================
# ROUTES UTILITAIRES POUR LE FRONTEND
# ===========================================

@app.route("/api/devis/etats", methods=["GET"])
@token_required
@permission_required('devis_view')
def get_devis_etats(current_user_id):
    """Récupérer les états possibles pour les devis"""
    return jsonify(["Validé", "Transformé en facture"]), 200

@app.route("/api/factures/etats", methods=["GET"])
@token_required
@permission_required('factures_view')
def get_factures_etats(current_user_id):
    """Récupérer les états possibles pour les factures"""
    return jsonify(["A envoyer au client", "En attente de payement", "Payée"]), 200

@app.route("/api/devis/<devis_id>/transform-to-facture", methods=["POST"])
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
            "document": "",
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
        return jsonify({"message": f"Erreur lors de la transformation: {str(e)}"}), 500

# ===== ROUTES POUR LES CATÉGORIES DE LIENS =====

@app.route('/api/link-categories', methods=['GET'])
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

@app.route('/api/link-categories/<category_id>', methods=['GET'])
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

@app.route('/api/link-categories', methods=['POST'])
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

@app.route('/api/link-categories/<category_id>', methods=['PUT'])
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

@app.route('/api/link-categories/<category_id>', methods=['DELETE'])
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

@app.route('/api/offer-categories', methods=['GET'])
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

@app.route('/api/offer-categories/<category_id>', methods=['GET'])
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

@app.route('/api/offer-categories', methods=['POST'])
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

@app.route('/api/offer-categories/<category_id>', methods=['PUT'])
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

@app.route('/api/offer-categories/<category_id>', methods=['DELETE'])
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

@app.route('/api/links', methods=['GET'])
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

@app.route('/api/links/<link_id>', methods=['GET'])
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

@app.route('/api/links', methods=['POST'])
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
            from urllib.parse import urlparse
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

@app.route('/api/links/<link_id>', methods=['PUT'])
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
                from urllib.parse import urlparse
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

@app.route('/api/links/<link_id>', methods=['DELETE'])
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

@app.route('/api/quote-statuses', methods=['GET'])
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

@app.route('/api/quote-statuses/<status_id>', methods=['GET'])
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

@app.route('/api/quote-statuses', methods=['POST'])
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

@app.route('/api/quote-statuses/<status_id>', methods=['PUT'])
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

@app.route('/api/quote-statuses/<status_id>', methods=['DELETE'])
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

@app.route('/api/invoice-statuses', methods=['GET'])
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

@app.route('/api/invoice-statuses/<status_id>', methods=['GET'])
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

@app.route('/api/invoice-statuses', methods=['POST'])
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

@app.route('/api/invoice-statuses/<status_id>', methods=['PUT'])
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

@app.route('/api/invoice-statuses/<status_id>', methods=['DELETE'])
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

@app.route('/api/offer-statuses', methods=['GET'])
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

@app.route('/api/offer-statuses/<status_id>', methods=['GET'])
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

@app.route('/api/offer-statuses', methods=['POST'])
def create_offer_status():
    """Créer un nouveau statut d'offre"""
    try:
        data = request.get_json()
        nom = data.get('nom')
        couleur = data.get('couleur')
        
        if not nom or not couleur:
            return jsonify({"message": "Nom et couleur sont requis"}), 400
        
        existing = offer_statuses_col.find_one({"nom": nom})
        if existing:
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
        status_data['_id'] = str(result.inserted_id)
        return jsonify(status_data), 201
        
    except Exception as e:
        print(f"Erreur lors de la création du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500

@app.route('/api/offer-statuses/<status_id>', methods=['PUT'])
def update_offer_status(status_id):
    """Modifier un statut d'offre"""
    try:
        data = request.get_json()
        
        status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        nom = data.get('nom')
        if nom and nom != status['nom']:
            existing = offer_statuses_col.find_one({"nom": nom})
            if existing:
                return jsonify({"message": "Ce statut existe déjà"}), 400
        
        update_data = {
            "nom": data.get('nom', status['nom']),
            "couleur": data.get('couleur', status['couleur']),
            "description": data.get('description', status['description']),
            "ordre": data.get('ordre', status['ordre']),
            "updatedAt": datetime.utcnow()
        }
        
        offer_statuses_col.update_one(
            {"_id": ObjectId(status_id)},
            {"$set": update_data}
        )
        
        updated_status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        updated_status['_id'] = str(updated_status['_id'])
        return jsonify(updated_status)
        
    except Exception as e:
        print(f"Erreur lors de la modification du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500

@app.route('/api/offer-statuses/<status_id>', methods=['DELETE'])
def delete_offer_status(status_id):
    """Supprimer un statut d'offre"""
    try:
        status = offer_statuses_col.find_one({"_id": ObjectId(status_id)})
        if not status:
            return jsonify({"message": "Statut non trouvé"}), 404
        
        offer_statuses_col.delete_one({"_id": ObjectId(status_id)})
        return jsonify({"message": "Statut supprimé avec succès"})
        
    except Exception as e:
        print(f"Erreur lors de la suppression du statut: {e}")
        return jsonify({"message": "Erreur serveur"}), 500



# ===== GESTION DES ERREURS =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({"message": "Endpoint non trouvé"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"message": "Erreur serveur interne"}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug, host="0.0.0.0", port=port)


# from bcrypt import hashpw, gensalt

# password = "admin123"  # mot de passe en clair
# hashed = hashpw(password.encode('utf-8'), gensalt())
# print(hashed.decode())  # tu obtiens la version cryptée à mettre dans MongoDB

# password_user = "user123"
# hashed_user = hashpw(password_user.encode('utf-8'), gensalt())
# print(hashed_user.decode())
