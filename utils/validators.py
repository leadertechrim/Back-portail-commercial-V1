"""Fonctions de validation pour les données"""
import re
from datetime import datetime
from bson.objectid import ObjectId


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
        datetime.fromisoformat(date_limite.replace('Z', '+00:00'))
        return True
    except:
        return False


def validate_offre_responsable_id(responsable_id):
    """Valider l'ID du responsable"""
    from bson.objectid import ObjectId
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
    from database import roles_collection, users_col
    
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

