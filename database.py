"""Module de gestion de la connexion MongoDB"""
import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Configuration MongoDB (exportée pour utilisation dans app.py)
# ⚠️ SÉCURITÉ : Ne jamais hardcoder les identifiants MongoDB
# Utiliser uniquement la variable d'environnement MONGO_URI
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    raise ValueError(
        "❌ ERREUR CRITIQUE : La variable d'environnement MONGO_URI n'est pas définie. "
        "Veuillez la configurer dans votre fichier .env ou dans les variables d'environnement de votre plateforme de déploiement."
    )

# Connexion MongoDB
client = MongoClient(MONGO_URI)
db = client.appels_doffres_db_copy

# Collections principales
sources_col = db.appels_doffres_sourcess  # Collection avec double 's' comme dans votre base
users_col = db.users
offres_col = db.offres
calls_for_tender_col = db.calls_for_tender
clients_col = db.Clients
partenaires_col = db.Partenaires
personnels_col = db.Personnels
devis_col = db.devis
factures_col = db.factures

# Collections pour les catégories et statuts
link_categories_col = db.link_categories
offer_categories_col = db.offer_categories
links_col = db.links
quote_statuses_col = db.quote_statuses
invoice_statuses_col = db.invoice_statuses
offer_statuses_col = db.offer_statuses

# Collections pour les rôles et permissions
roles_collection = db.roles
permissions_collection = db.permissions

