"""Fonctions pour la gestion des permissions et rôles"""
from database import roles_collection, permissions_collection


def user_has_permission(user, permission_name):
    """Vérifie si un utilisateur a une permission spécifique"""
    # Les admins ont toutes les permissions
    admin_roles = ['admin', 'Admin', 'SupAdmin', 'directeur', 'Superviseur']
    if user.get('role') in admin_roles:
        return True
    
    # Récupérer les permissions du rôle depuis la base - chercher par nom
    user_role = user.get('role', 'spectateur')
    role = roles_collection.find_one({'nom': user_role})
    if role:
        return permission_name in role.get('permissions', [])
    
    return False


def get_user_permissions(user):
    """Récupère toutes les permissions d'un utilisateur"""
    # Les admins ont toutes les permissions
    admin_roles = ['admin', 'Admin', 'SupAdmin', 'directeur', 'Superviseur']
    if user.get('role') in admin_roles:
        return [p['nom'] for p in permissions_collection.find()]
    
    # Récupérer les permissions du rôle depuis la base - chercher par nom
    user_role = user.get('role', 'spectateur')
    role = roles_collection.find_one({'nom': user_role})
    if role:
        return role.get('permissions', [])
    
    return []













