"""Gestionnaire d'erreurs sécurisé pour l'API"""
import logging
import os

# Configuration du logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.ERROR)

def handle_server_error(error, context="opération"):
    """
    Gère les erreurs serveur de manière sécurisée.
    Log les détails techniques, mais retourne un message générique à l'utilisateur.
    
    Args:
        error: L'exception capturée
        context: Contexte de l'opération (ex: "création de l'offre")
    
    Returns:
        tuple: (message_json, status_code)
    """
    # Logger les détails techniques (visible uniquement dans les logs serveur)
    logger.error(f"Erreur lors de la {context}: {str(error)}", exc_info=True)
    
    # Retourner un message générique à l'utilisateur
    return {"message": "Une erreur est survenue. Veuillez réessayer plus tard."}, 500


def handle_validation_error(field_name=None, custom_message=None):
    """
    Gère les erreurs de validation de manière standardisée.
    
    Args:
        field_name: Nom du champ en erreur
        custom_message: Message personnalisé
    
    Returns:
        tuple: (message_json, status_code)
    """
    if custom_message:
        return {"message": custom_message}, 400
    
    if field_name:
        return {"message": f"Le champ '{field_name}' est invalide"}, 400
    
    return {"message": "Données invalides"}, 400

