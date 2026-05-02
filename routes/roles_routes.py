"""Routes pour la gestion des rôles et permissions"""
from flask import Blueprint, request, jsonify, current_app
from bson.objectid import ObjectId
from datetime import datetime
from database import roles_collection, permissions_collection, users_col
from auth.decorators import token_required, permission_required, admin_required
from auth.permissions import user_has_permission, get_user_permissions
from utils.validators import validate_role_data, validate_permission_data, sanitize_input
from utils.error_handler import handle_server_error

roles_bp = Blueprint('roles', __name__)

# Fonctions utilitaires locales (à extraire dans utils plus tard)
def rate_limit_check(user_id, action, limit=10, window=60):
    """Vérifier les limites de taux pour éviter les abus"""
    return True  # Pas de limite pour l'instant

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
    except Exception as e:
        print(f"Erreur lors de l'enregistrement de l'audit: {e}")


# =============================================================================
# ROUTES POUR LES RÔLES
# =============================================================================

@roles_bp.route("/api/roles", methods=["GET"])
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
        message, status = handle_server_error(e, "récupération des rôles")
        return jsonify(message), status

@roles_bp.route("/api/roles/<role_id>", methods=["GET"])
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
        message, status = handle_server_error(e, "récupération du rôle")
        return jsonify(message), status

@roles_bp.route("/api/roles", methods=["POST"])
@token_required
@admin_required
def create_role(current_user_id):
    """Créer un rôle (admin seulement)"""
    try:
        data = request.get_json()
        data = sanitize_input(data)
        
        validation_errors = validate_role_data(data)
        if validation_errors:
            return jsonify({
                'message': 'Erreurs de validation',
                'errors': validation_errors
            }), 400
        
        if not rate_limit_check(current_user_id, 'create_role'):
            return jsonify({'message': 'Trop de requêtes. Veuillez patienter.'}), 429
        
        existing_role = roles_collection.find_one({'nom': data['nom']})
        if existing_role:
            return jsonify({'message': 'Un rôle avec ce nom existe déjà'}), 400
        
        max_order = roles_collection.find().sort("ordre", -1).limit(1)
        next_order = 1
        for role in max_order:
            next_order = role.get('ordre', 0) + 1
            break
        
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
        audit_log(current_user_id, 'create_role', {'role_name': data['nom']})
        
        return jsonify({
            'message': 'Rôle créé avec succès',
            'data': role_data
        }), 201
    except Exception as e:
        message, status = handle_server_error(e, "création du rôle")
        return jsonify(message), status

@roles_bp.route("/api/roles/<role_id>", methods=["PUT"])
@token_required
@admin_required
def update_role(current_user_id, role_id):
    """Modifier un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        existing_role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not existing_role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        if 'nom' in data and data['nom'] != existing_role['nom']:
            duplicate_role = roles_collection.find_one({
                'nom': data['nom'],
                '_id': {'$ne': ObjectId(role_id)}
            })
            if duplicate_role:
                return jsonify({'message': 'Un rôle avec ce nom existe déjà'}), 400
        
        update_data = {'updated_at': datetime.utcnow()}
        allowed_fields = ['nom', 'description', 'couleur', 'ordre', 'permissions']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        roles_collection.update_one(
            {'_id': ObjectId(role_id)},
            {'$set': update_data}
        )
        
        updated_role = roles_collection.find_one({'_id': ObjectId(role_id)})
        updated_role['_id'] = str(updated_role['_id'])
        
        return jsonify({
            'message': 'Rôle modifié avec succès',
            'data': updated_role
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "modification du rôle")
        return jsonify(message), status

@roles_bp.route("/api/roles/<role_id>", methods=["DELETE"])
@token_required
@admin_required
def delete_role(current_user_id, role_id):
    """Supprimer un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        users_with_role = users_col.count_documents({'role': role.get('nom', '')})
        if users_with_role > 0:
            return jsonify({
                'message': f'Impossible de supprimer le rôle. {users_with_role} utilisateur(s) l\'utilisent encore'
            }), 400
        
        roles_collection.delete_one({'_id': ObjectId(role_id)})
        
        return jsonify({
            'message': 'Rôle supprimé avec succès'
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "suppression du rôle")
        return jsonify(message), status


# =============================================================================
# ROUTES POUR LES PERMISSIONS
# =============================================================================

@roles_bp.route("/api/permissions", methods=["GET"])
@token_required
def get_permissions(current_user_id):
    """Récupérer toutes les permissions"""
    try:
        permissions = list(permissions_collection.find().sort("category", 1))
        for permission in permissions:
            permission['_id'] = str(permission['_id'])
        
        return jsonify({
            'message': 'Permissions récupérées avec succès',
            'data': permissions
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "récupération des permissions")
        return jsonify(message), status

@roles_bp.route("/api/user/permissions", methods=["GET"])
@token_required
def get_current_user_permissions(current_user_id):
    """Récupérer les permissions de l'utilisateur actuel"""
    try:
        user = users_col.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({"message": "Utilisateur non trouvé"}), 404
        
        user_role = user.get("role")
        role_doc = roles_collection.find_one({"nom": user_role})
        
        if not role_doc:
            normalized_role = (user_role or "").strip().lower()
            privileged_roles = ["admin", "supadmin", "administrateur principal", "administrateur système"]
            
            if normalized_role in privileged_roles:
                all_permissions = [p["nom"] for p in permissions_collection.find()]
                return jsonify({
                    "message": "Permissions récupérées avec succès (rôle privilégié)",
                    "data": {
                        "permissions": all_permissions,
                        "role": user_role,
                        "user_id": current_user_id,
                        "is_privileged": True
                    }
                }), 200
            
            return jsonify({
                "message": f"Rôle '{user_role}' inexistant en base de données",
                "error": "role_not_found"
            }), 400
        
        permissions = role_doc.get("permissions", [])
        
        return jsonify({
            "message": "Permissions récupérées avec succès",
            "data": {
                "permissions": permissions,
                "role": user_role,
                "user_id": current_user_id
            }
        })
    except Exception as e:
        message, status = handle_server_error(e, "suppression du rôle")
        return jsonify(message), status

@roles_bp.route("/api/users/<user_id>/permissions", methods=["GET"])
@token_required
@admin_required
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
        message, status = handle_server_error(e, "récupération des permissions utilisateur")
        return jsonify(message), status

@roles_bp.route("/api/users/<user_id>/assign-role", methods=["POST"])
@token_required
@admin_required
def assign_role_to_user(current_user_id, user_id):
    """Assigner un rôle à un utilisateur (admin seulement)"""
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'ID utilisateur invalide'}), 400
        
        data = request.get_json()
        if 'role' not in data:
            return jsonify({'message': 'Champ "role" requis'}), 400
        
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        role = roles_collection.find_one({'nom': data['role']})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'role': data['role'], 'updated_at': datetime.utcnow()}}
        )
        
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
        message, status = handle_server_error(e, "assignation du rôle")
        return jsonify(message), status

@roles_bp.route("/api/users/<user_id>/remove-role", methods=["POST"])
@token_required
@admin_required
def remove_role_from_user(current_user_id, user_id):
    """Retirer un rôle d'un utilisateur (admin seulement)"""
    try:
        if not ObjectId.is_valid(user_id):
            return jsonify({'message': 'ID utilisateur invalide'}), 400
        
        user = users_col.find_one({'_id': ObjectId(user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        users_col.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'role': 'spectateur', 'updated_at': datetime.utcnow()}}
        )
        
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
        message, status = handle_server_error(e, "retrait du rôle utilisateur")
        return jsonify(message), status

# =============================================================================
# ROUTES UTILITAIRES
# =============================================================================

@roles_bp.route("/api/roles/init", methods=["POST"])
@token_required
@admin_required
def init_roles_and_permissions(current_user_id):
    """Initialiser les rôles et permissions par défaut (admin seulement)"""
    try:
        roles_collection.drop()
        permissions_collection.drop()
        
        permissions_data = [
            {"nom": "view_offers", "description": "Voir les offres", "category": "Offres"},
            {"nom": "create_offers", "description": "Créer des offres", "category": "Offres"},
            {"nom": "edit_offers", "description": "Modifier les offres", "category": "Offres"},
            {"nom": "delete_offers", "description": "Supprimer les offres", "category": "Offres"},
            {"nom": "view_quotes", "description": "Voir les devis", "category": "Devis"},
            {"nom": "create_quotes", "description": "Créer des devis", "category": "Devis"},
            {"nom": "edit_quotes", "description": "Modifier les devis", "category": "Devis"},
            {"nom": "delete_quotes", "description": "Supprimer les devis", "category": "Devis"},
            {"nom": "view_invoices", "description": "Voir les factures", "category": "Factures"},
            {"nom": "create_invoices", "description": "Créer des factures", "category": "Factures"},
            {"nom": "edit_invoices", "description": "Modifier les factures", "category": "Factures"},
            {"nom": "delete_invoices", "description": "Supprimer les factures", "category": "Factures"},
            {"nom": "view_clients", "description": "Voir les clients", "category": "Clients"},
            {"nom": "create_clients", "description": "Créer des clients", "category": "Clients"},
            {"nom": "edit_clients", "description": "Modifier les clients", "category": "Clients"},
            {"nom": "delete_clients", "description": "Supprimer les clients", "category": "Clients"},
            {"nom": "view_personnel", "description": "Voir le personnel", "category": "Personnel"},
            {"nom": "create_personnel", "description": "Créer du personnel", "category": "Personnel"},
            {"nom": "edit_personnel", "description": "Modifier le personnel", "category": "Personnel"},
            {"nom": "delete_personnel", "description": "Supprimer le personnel", "category": "Personnel"},
            {"nom": "view_partners", "description": "Voir les partenaires", "category": "Partenaires"},
            {"nom": "create_partners", "description": "Créer des partenaires", "category": "Partenaires"},
            {"nom": "edit_partners", "description": "Modifier les partenaires", "category": "Partenaires"},
            {"nom": "delete_partners", "description": "Supprimer les partenaires", "category": "Partenaires"},
            {"nom": "view_sources", "description": "Voir les sources", "category": "Sources"},
            {"nom": "create_sources", "description": "Créer des sources", "category": "Sources"},
            {"nom": "edit_sources", "description": "Modifier les sources", "category": "Sources"},
            {"nom": "delete_sources", "description": "Supprimer les sources", "category": "Sources"},
            {"nom": "admin_settings", "description": "Gérer les paramètres", "category": "Administration"},
            {"nom": "manage_users", "description": "Gérer les utilisateurs", "category": "Administration"},
            {"nom": "manage_roles", "description": "Gérer les rôles", "category": "Administration"},
            {"nom": "view_analytics", "description": "Voir les analyses", "category": "Administration"},
            {"nom": "view_reports", "description": "Voir les rapports", "category": "Rapports"},
            {"nom": "export_data", "description": "Exporter les données", "category": "Rapports"}
        ]
        
        for perm in permissions_data:
            perm['created_at'] = datetime.utcnow()
        
        permissions_collection.insert_many(permissions_data)
        
        roles_data = [
            {
                "nom": "admin",
                "description": "Administrateur avec tous les droits",
                "couleur": "#dc3545",
                "ordre": 1,
                "permissions": [p['nom'] for p in permissions_data],
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
                "permissions": ["view_offers", "view_quotes", "view_invoices"],
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
        message, status = handle_server_error(e, "initialisation des rôles et permissions")
        return jsonify(message), status

@roles_bp.route("/api/test-permission/<permission_name>", methods=["GET"])
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
        message, status = handle_server_error(e, "test de permission")
        return jsonify(message), status

@roles_bp.route("/api/users-with-roles", methods=["GET"])
@token_required
@admin_required
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
        message, status = handle_server_error(e, "récupération des utilisateurs avec rôles")
        return jsonify(message), status


# =============================================================================
# ROUTES POUR LA GESTION DYNAMIQUE DES PERMISSIONS
# =============================================================================

@roles_bp.route("/api/permissions", methods=["POST"])
@token_required
@admin_required
def create_permission(current_user_id):
    """Créer une nouvelle permission (admin seulement)"""
    try:
        data = request.get_json()
        
        required_fields = ['nom', 'description', 'category']
        for field in required_fields:
            if field not in data:
                return jsonify({'message': f'Champ "{field}" requis'}), 400
        
        existing_permission = permissions_collection.find_one({'nom': data['nom']})
        if existing_permission:
            return jsonify({'message': 'Une permission avec ce nom existe déjà'}), 400
        
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
        message, status = handle_server_error(e, "création de la permission")
        return jsonify(message), status

@roles_bp.route("/api/permissions/<permission_id>", methods=["PUT"])
@token_required
@admin_required
def update_permission(current_user_id, permission_id):
    """Modifier une permission (admin seulement)"""
    try:
        if not ObjectId.is_valid(permission_id):
            return jsonify({'message': 'ID de permission invalide'}), 400
        
        data = request.get_json()
        existing_permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        if not existing_permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        if 'nom' in data and data['nom'] != existing_permission['nom']:
            duplicate_permission = permissions_collection.find_one({
                'nom': data['nom'],
                '_id': {'$ne': ObjectId(permission_id)}
            })
            if duplicate_permission:
                return jsonify({'message': 'Une permission avec ce nom existe déjà'}), 400
        
        update_data = {}
        allowed_fields = ['nom', 'description', 'category']
        for field in allowed_fields:
            if field in data:
                update_data[field] = data[field]
        
        permissions_collection.update_one(
            {'_id': ObjectId(permission_id)},
            {'$set': update_data}
        )
        
        updated_permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        updated_permission['_id'] = str(updated_permission['_id'])
        
        return jsonify({
            'message': 'Permission modifiée avec succès',
            'data': updated_permission
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "modification de la permission")
        return jsonify(message), status

@roles_bp.route("/api/permissions/<permission_id>", methods=["DELETE"])
@token_required
@admin_required
def delete_permission(current_user_id, permission_id):
    """Supprimer une permission (admin seulement)"""
    try:
        if not ObjectId.is_valid(permission_id):
            return jsonify({'message': 'ID de permission invalide'}), 400
        
        permission = permissions_collection.find_one({'_id': ObjectId(permission_id)})
        if not permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        roles_with_permission = roles_collection.count_documents({
            'permissions': permission['nom']
        })
        if roles_with_permission > 0:
            return jsonify({
                'message': f'Impossible de supprimer la permission. {roles_with_permission} rôle(s) l\'utilisent encore'
            }), 400
        
        permissions_collection.delete_one({'_id': ObjectId(permission_id)})
        
        return jsonify({
            'message': 'Permission supprimée avec succès'
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "suppression de la permission")
        return jsonify(message), status


# =============================================================================
# ROUTES POUR LA GESTION DYNAMIQUE AVANCÉE
# =============================================================================

@roles_bp.route("/api/roles/<role_id>/permissions", methods=["POST"])
@token_required
@admin_required
def add_permission_to_role(current_user_id, role_id):
    """Ajouter une permission à un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        if 'permission' not in data:
            return jsonify({'message': 'Champ "permission" requis'}), 400
        
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        permission = permissions_collection.find_one({'nom': data['permission']})
        if not permission:
            return jsonify({'message': 'Permission non trouvée'}), 404
        
        if data['permission'] not in role.get('permissions', []):
            roles_collection.update_one(
                {'_id': ObjectId(role_id)},
                {'$push': {'permissions': data['permission']}, '$set': {'updated_at': datetime.utcnow()}}
            )
        
        return jsonify({
            'message': 'Permission ajoutée au rôle avec succès'
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "ajout de la permission au rôle")
        return jsonify(message), status

@roles_bp.route("/api/roles/<role_id>/permissions", methods=["DELETE"])
@token_required
@admin_required
def remove_permission_from_role(current_user_id, role_id):
    """Retirer une permission d'un rôle (admin seulement)"""
    try:
        if not ObjectId.is_valid(role_id):
            return jsonify({'message': 'ID de rôle invalide'}), 400
        
        data = request.get_json()
        if 'permission' not in data:
            return jsonify({'message': 'Champ "permission" requis'}), 400
        
        role = roles_collection.find_one({'_id': ObjectId(role_id)})
        if not role:
            return jsonify({'message': 'Rôle non trouvé'}), 404
        
        roles_collection.update_one(
            {'_id': ObjectId(role_id)},
            {'$pull': {'permissions': data['permission']}, '$set': {'updated_at': datetime.utcnow()}}
        )
        
        return jsonify({
            'message': 'Permission retirée du rôle avec succès'
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "retrait de la permission du rôle")
        return jsonify(message), status

@roles_bp.route("/api/roles/bulk-update", methods=["POST"])
@token_required
@admin_required
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
                
                update_data = {'updated_at': datetime.utcnow()}
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
                errors.append(f'Erreur pour le rôle {role_data.get("nom", "Inconnu")}')
        
        return jsonify({
            'message': f'Mise à jour terminée: {updated_count} rôles mis à jour',
            'updated_count': updated_count,
            'errors': errors
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "mise à jour en lot des rôles")
        return jsonify(message), status

@roles_bp.route("/api/permissions/categories", methods=["GET"])
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
        message, status = handle_server_error(e, "récupération des catégories de permissions")
        return jsonify(message), status

@roles_bp.route("/api/roles/export", methods=["GET"])
@token_required
@admin_required
def export_roles_and_permissions(current_user_id):
    """Exporter tous les rôles et permissions (admin seulement)"""
    try:
        roles = list(roles_collection.find().sort("ordre", 1))
        for role in roles:
            role['_id'] = str(role['_id'])
        
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
        message, status = handle_server_error(e, "export des rôles et permissions")
        return jsonify(message), status

@roles_bp.route("/api/roles/import", methods=["POST"])
@token_required
@admin_required
def import_roles_and_permissions(current_user_id):
    """Importer des rôles et permissions (admin seulement)"""
    try:
        data = request.get_json()
        
        if 'roles' not in data and 'permissions' not in data:
            return jsonify({'message': 'Données d\'import invalides'}), 400
        
        imported_roles = 0
        imported_permissions = 0
        errors = []
        
        if 'permissions' in data:
            for perm_data in data['permissions']:
                try:
                    existing = permissions_collection.find_one({'nom': perm_data['nom']})
                    if not existing:
                        perm_data['created_at'] = datetime.utcnow()
                        permissions_collection.insert_one(perm_data)
                        imported_permissions += 1
                except Exception as e:
                    errors.append(f'Erreur permission {perm_data.get("nom", "Inconnu")}')
        
        if 'roles' in data:
            for role_data in data['roles']:
                try:
                    existing = roles_collection.find_one({'nom': role_data['nom']})
                    if not existing:
                        role_data['created_at'] = datetime.utcnow()
                        role_data['updated_at'] = datetime.utcnow()
                        roles_collection.insert_one(role_data)
                        imported_roles += 1
                except Exception as e:
                    errors.append(f'Erreur rôle {role_data.get("nom", "Inconnu")}')
        
        return jsonify({
            'message': f'Import terminé: {imported_roles} rôles, {imported_permissions} permissions importés',
            'imported_roles': imported_roles,
            'imported_permissions': imported_permissions,
            'errors': errors
        }), 200
    except Exception as e:
        message, status = handle_server_error(e, "import des rôles et permissions")
        return jsonify(message), status

