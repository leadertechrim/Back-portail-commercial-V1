"""Décorateurs pour l'authentification et les permissions"""
from functools import wraps
from flask import request, jsonify, current_app
import jwt
from bson.objectid import ObjectId
from database import users_col
from auth.permissions import get_user_permissions


def token_required(f):
    """Décorateur pour vérifier le token JWT"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.startswith('Bearer '):
            return jsonify({'message': 'Token manquant'}), 401
        
        try:
            token = token[7:]  # Enlever "Bearer "
            data = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_id = data['user_id']
            
            # Charger l'utilisateur complet et ses permissions pour les routes qui en ont besoin
            user_doc = users_col.find_one({'_id': ObjectId(current_user_id)})
            if not user_doc:
                return jsonify({'message': 'Utilisateur non trouvé'}), 404
            
            request.current_user = {
                'user_id': str(user_doc['_id']),
                'role': user_doc.get('role', ''),
                'email': user_doc.get('email', ''),
                'name': user_doc.get('name', ''),
                'permissions': get_user_permissions(user_doc)
            }
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
            from auth.permissions import user_has_permission
            
            user = users_col.find_one({'_id': ObjectId(current_user_id)})
            if not user:
                return jsonify({'message': 'Utilisateur non trouvé'}), 404
            
            if not user_has_permission(user, permission_name):
                return jsonify({'message': f'Permission "{permission_name}" requise'}), 403
            
            return f(current_user_id, *args, **kwargs)
        return decorated
    return decorator


def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est admin"""
    @wraps(f)
    def decorated(current_user_id, *args, **kwargs):
        user = users_col.find_one({'_id': ObjectId(current_user_id)})
        if not user:
            return jsonify({'message': 'Utilisateur non trouvé'}), 404
        
        admin_roles = ['admin', 'Admin', 'SupAdmin', 'directeur', 'Superviseur']
        if user.get('role') not in admin_roles:
            return jsonify({'message': 'Accès administrateur requis'}), 403
        
        return f(current_user_id, *args, **kwargs)
    return decorated

