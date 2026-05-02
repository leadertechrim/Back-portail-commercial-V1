import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import threading
import time

# Imports des modules refactorisés
from config import create_app
from database import (
    client, db, sources_col, users_col, offres_col, calls_for_tender_col,
    clients_col, partenaires_col, personnels_col, devis_col, factures_col,
    link_categories_col, offer_categories_col, links_col,
    quote_statuses_col, invoice_statuses_col, offer_statuses_col,
    roles_collection, permissions_collection, MONGO_URI
)
from auth.decorators import token_required, permission_required, admin_required
from auth.permissions import user_has_permission, get_user_permissions
from utils.validators import (
    validate_email, validate_password, validate_telephone, validate_whatsapp,
    validate_adresse, validate_statut, validate_user_fonction, validate_role_data,
    validate_permission_data, validate_user_role_assignment, sanitize_input,
    validate_raison_sociale, validate_nom_prenom, validate_note_commentaire,
    validate_offre_intitulee, validate_offre_lien, validate_offre_client,
    validate_offre_date_limite, validate_offre_responsable_id, validate_offre_categorie,
    validate_offre_numero, validate_offre_partenaire, validate_offre_documents,
    validate_documents_array
)
from routes.auth_routes import auth_bp
from routes.roles_routes import roles_bp
from routes.sources_routes import sources_bp
from routes.debug_routes import debug_bp
from routes.users_routes import users_bp
from routes.clients_routes import clients_bp
from routes.partenaires_routes import partenaires_bp
from routes.personnels_routes import personnels_bp
from routes.offres_routes import offres_bp
from routes.devis_routes import devis_bp
from routes.factures_routes import factures_bp
from routes.categories_routes import categories_bp

# Créer l'application Flask avec la configuration des modules
app = create_app()

# Configuration CORS
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)


# Configuration Bcrypt
bcrypt = app.bcrypt

# Enregistrer les Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(roles_bp)
app.register_blueprint(sources_bp)
app.register_blueprint(debug_bp)
app.register_blueprint(users_bp)
app.register_blueprint(clients_bp)
app.register_blueprint(partenaires_bp)
app.register_blueprint(personnels_bp)
app.register_blueprint(offres_bp)
app.register_blueprint(devis_bp)
app.register_blueprint(factures_bp)
app.register_blueprint(categories_bp)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def rate_limit_check(user_id, action, limit=10, window=60):
    """Vérifier les limites de taux pour éviter les abus"""
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

# ===== GESTION DES ERREURS =====

@app.errorhandler(404)
def not_found(error):
    """Gérer les erreurs 404 (route non trouvée)"""
    # Logger les tentatives d'accès à des routes inexistantes
    if request.path not in ['/loginMsg.js', '/cgi/get.cgi']:  # Ignorer les scans automatiques courants
        print(f"⚠️ 404 - Route non trouvée: {request.method} {request.path} depuis {request.remote_addr}")
    
    # Si c'est une requête API, retourner du JSON
    if request.path.startswith('/api/'):
        return jsonify({"message": "Endpoint non trouvé"}), 404
    
    # Sinon, retourner une page HTML ou rediriger
    return jsonify({"message": "Endpoint non trouvé", "path": request.path}), 404


@app.errorhandler(400)
def bad_request(error):
    """Gérer les erreurs 400 (requête malformée)"""
    print(f"⚠️ 400 - Requête malformée: {request.method} {request.path} depuis {request.remote_addr}")
    return jsonify({"message": "Requête malformée"}), 400


@app.errorhandler(500)
def internal_error(error):
    """Gérer les erreurs 500 (erreur serveur)"""
    print(f"❌ 500 - Erreur serveur: {request.method} {request.path} depuis {request.remote_addr}")
    return jsonify({"message": "Erreur serveur interne"}), 500


# ============================================================
# APPELS D'OFFRES IA - Intégration Module
# ============================================================
try:
    from routes_offres_ia import register_offres_ia_routes
    
    # Utiliser la connexion MongoDB existante depuis database.py
    try:
        # db est déjà importé depuis database.py en haut du fichier
        from database import db as db_offres
    except:
        # Si erreur, essayer d'importer directement
        from database import db
        db_offres = db
    
    if db_offres is not None:
        register_offres_ia_routes(app, db_offres, token_required, permission_required)
        print("✅ Module Appels d'Offres IA chargé avec succès")
    else:
        print("⚠️ Base de données non disponible pour module Offres IA")
except Exception as e:
    print(f"⚠️ Module Offres IA non chargé : {e}")
    # import traceback
    # traceback.print_exc()
# ============================================================


# =============================================================================
# SCRAPING AUTOMATIQUE EN TEMPS RÉEL
# =============================================================================

def background_scraper():
    """
    Scraping automatique en arrière-plan toutes les heures
    Pour développement local uniquement.
    """
    print("\n🤖 Thread de scraping automatique démarré")
    
    # Attendre 10 secondes que Flask démarre complètement
    time.sleep(10)
    
    while True:
        try:
            # Importer et lancer le scraper continu (utilisé en production via start.py)
            try:
                from scraper_continuous import run_continuous_scraper
                # Ne pas lancer en boucle ici car c'est déjà géré par scraper_continuous
                print("⚠️ Utilisez start.py pour le scraping en production")
            except ImportError:
                print("⚠️ scraper_continuous.py non trouvé - scraping désactivé")
            
        except Exception as e:
            print(f"\n❌ Erreur scraping automatique : {e}")
        
        # Attendre 1 heure (3600 secondes)
        time.sleep(3600)


if __name__ == "__main__":
    print("\n" + "="*70)
    print(" "*15 + "🚀 DÉMARRAGE DU SERVEUR APLOFR (MODE DÉVELOPPEMENT)")
    print("="*70)
    print("📡 Backend Flask API : https://back-portail-commercial-32528505fc5a.herokuapp.com/")
    print("⚠️  Pour la production, utilisez start.py")
    print("="*70 + "\n")
    
    # Lancer le thread de scraping automatique (optionnel, souvent mieux via start.py)
    # scraper_thread = threading.Thread(target=background_scraper, daemon=True)
    # scraper_thread.start()
    
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"
    app.run(debug=debug, host='0.0.0.0', port=port, use_reloader=False)
