"""
Routes pour les Appels d'Offres IA
À importer dans votre app.py existant
"""
from flask import jsonify, request
from functools import wraps
from datetime import datetime

# Ces routes seront enregistrées dans votre app Flask existant
def register_offres_ia_routes(app, db, token_required, permission_required):
    """
    Enregistre les routes Appels d'Offres IA dans votre app Flask
    
    Usage dans app.py:
        from routes_offres_ia import register_offres_ia_routes
        register_offres_ia_routes(app, db, token_required, permission_required)
    """
    
    # Collections MongoDB
    liens_collection = db["appels_doffres_liens_new"]
    sources_collection = db["appels_doffres_sources"]
    
    
    @app.route('/api/offres-ia/statistiques', methods=['GET'])
    @token_required
    def get_stats_offres_ia(current_user_id):
        """Statistiques des appels d'offres IA avec seuil 60%"""
        try:
            # Total = TOUS les liens VISIBLES (masque=false, en_corbeille=false)
            total = liens_collection.count_documents({
                "masque": {"$ne": True},
                "est_masque": {"$ne": True},
                "en_corbeille": {"$ne": True}
            })
            
            # Informatique = IT visibles avec seuil 60% (est_informatique_ia=true, score >= 0.60, masque=false, en_corbeille=false)
            informatique = liens_collection.count_documents({
                "analysis_result.est_informatique_ia": True,
                "analysis_result.score": {"$gte": 0.60},
                "masque": {"$ne": True},
                "est_masque": {"$ne": True},
                "en_corbeille": {"$ne": True}
            })
        
            # Masqués = masqués temporairement (SANS corbeille, réversible)
            masques = liens_collection.count_documents({
                "$and": [
                    {
                        "$or": [
                            {"est_masque": True},
                            {"masque": True}
                        ]
                    },
                    {
                        "$or": [
                            {"en_corbeille": {"$exists": False}},
                            {"en_corbeille": False},
                            {"en_corbeille": None}
                        ]
                    }
                ]
            })
            
            # Corbeille = supprimés définitivement
            corbeille = liens_collection.count_documents({
                "en_corbeille": True
            })
            
            # Avec PDF = IT visibles avec PDF et seuil 60% (masque=false, en_corbeille=false, nb_pdf > 0)
            avec_pdf = liens_collection.count_documents({
                "analysis_result.est_informatique_ia": True,
                "analysis_result.score": {"$gte": 0.60},
                "nb_pdf": {"$gt": 0},
                "masque": {"$ne": True},
                "est_masque": {"$ne": True},
                "en_corbeille": {"$ne": True}
            })
            
            return jsonify({
                "total": total,
                "informatique": informatique,
                "masques": masques,
                "corbeille": corbeille,
                "avec_pdf": avec_pdf
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/informatique', methods=['GET'])
    @token_required
    def get_offres_informatiques(current_user_id):
        """
        Liste des appels d'offres informatiques
        EXCLUT LA CORBEILLE
        """
        try:
            # Récupérer TOUS les liens informatiques VISIBLES (NON masqués, NON en corbeille) avec seuil 60%
            offres = list(liens_collection.find(
                {
                    "$and": [
                        # Condition principale : informatique OU en attente
                        {
                            "$or": [
                                # Liens informatiques confirmés avec score >= 60%
                                {
                                    "est_appel_offres": True,
                                    "analysis_result.est_informatique_ia": True,
                                    "analysis_result.score": {"$gte": 0.60}
                                },
                                # Liens en attente d'analyse (affichés immédiatement)
                                {
                                    "statut_analyse": "en_attente"
                                },
                                # Liens en cours d'analyse
                                {
                                    "analysis_result.en_cours": True
                                }
                            ]
                        },
                        # Exclure masqués
                        {
                            "masque": {"$ne": True}
                        },
                        {
                            "est_masque": {"$ne": True}
                        },
                        # Exclure corbeille
                        {
                            "$or": [
                                {"en_corbeille": {"$exists": False}},
                                {"en_corbeille": False},
                                {"en_corbeille": None}
                            ]
                        }
                    ]
                },
                {"_id": 0}
            ).sort("date_added", -1).limit(500))
            
            return jsonify(offres)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/masquer', methods=['POST'])
    @token_required
    @permission_required('offres_ia_masquer')
    def masquer_offre(current_user_id):
        """Masque un appel d'offres (faux positif)"""
        try:
            print("=== DÉBUT MASQUER_OFFRE ===")
            print(f"current_user_id reçu: {current_user_id} (type: {type(current_user_id)})")
            
            # Récupérer l'utilisateur pour avoir son email
            from bson import ObjectId
            
            # S'assurer que current_user_id est bien une string
            if not isinstance(current_user_id, str):
                current_user_id = str(current_user_id)
            
            users_col = db.users
            
            # Récupérer l'utilisateur
            try:
                user = users_col.find_one({'_id': ObjectId(current_user_id)})
                if user and isinstance(user, dict):
                    user_email = user.get('email', 'unknown')
                    print(f"Utilisateur trouvé: {user_email}")
                else:
                    user_email = 'unknown'
                    print("Utilisateur non trouvé, utilisation de 'unknown'")
            except Exception as e:
                print(f"Erreur récupération utilisateur: {e}")
                user_email = 'unknown'
            
            # Récupérer les données JSON
            data = request.get_json()
            print(f"Données reçues - Type: {type(data)}, Valeur: {data}")
            
            if data is None:
                print("ERREUR: Pas de données JSON")
                return jsonify({"error": "Données manquantes"}), 400
            
            if not isinstance(data, dict):
                print(f"ERREUR: data n'est pas un dict mais {type(data)}")
                return jsonify({"error": "Format de données invalide"}), 400
                
            url = data.get('url')
            print(f"URL extraite: {url}")
            
            if not url:
                print("ERREUR: URL manquante")
                return jsonify({"error": "URL manquante"}), 400
            
            print(f"Tentative de masquage: {url}")
            
            # 👁️ MASQUAGE : Cacher temporairement (réversible, PAS en corbeille)
            result = liens_collection.update_one(
                {"url": url},
                {"$set": {
                    "est_masque": True,
                    "masque": True,
                    "en_corbeille": False,  # ✅ PAS en corbeille
                    "date_masquage": datetime.now(),
                    "masque_par": user_email,
                    "raison_masquage": data.get('raison', 'Non informatique - Faux positif')
                }}
            )
            
            print(f"Résultat update: modified_count={result.modified_count}")
            
            if result.modified_count > 0:
                print("=== SUCCÈS MASQUAGE ===")
                return jsonify({"success": True, "message": "Offre masquée"})
            else:
                print("=== ÉCHEC: Offre non trouvée ===")
                return jsonify({"error": "Offre non trouvée"}), 404
        except Exception as e:
            print(f"=== ERREUR EXCEPTION ===")
            print(f"Type: {type(e).__name__}")
            print(f"Message: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/demasquer', methods=['POST'])
    @token_required
    @permission_required('offres_ia_masquer')
    def demasquer_offre(current_user_id):
        """Démasque un appel d'offres"""
        try:
            # Récupérer l'utilisateur pour avoir son email
            from bson import ObjectId
            
            # S'assurer que current_user_id est bien une string
            if not isinstance(current_user_id, str):
                current_user_id = str(current_user_id)
            
            users_col = db.users
            
            # Récupérer l'utilisateur
            try:
                user = users_col.find_one({'_id': ObjectId(current_user_id)})
                if user and isinstance(user, dict):
                    user_email = user.get('email', 'unknown')
                else:
                    user_email = 'unknown'
            except Exception as e:
                print(f"Erreur récupération utilisateur: {e}")
                user_email = 'unknown'
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données manquantes"}), 400
                
            url = data.get('url') if isinstance(data, dict) else None
            
            if not url:
                return jsonify({"error": "URL manquante"}), 400
            
            result = liens_collection.update_one(
                {"url": url},
                {"$set": {
                    "est_masque": False,
                    "masque": False,
                    "date_demasquage": datetime.now(),
                    "demasque_par": user_email
                }}
            )
            
            if result.modified_count > 0:
                return jsonify({"success": True, "message": "Offre démasquée"})
            else:
                return jsonify({"error": "Offre non trouvée"}), 404
        except Exception as e:
            print(f"Erreur dans demasquer_offre: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/supprimer', methods=['POST'])
    @token_required
    @permission_required('offres_ia_supprimer')
    def supprimer_offre(current_user_id):
        """Met une offre en corbeille (suppression définitive)"""
        try:
            # Récupérer l'utilisateur pour avoir son email
            from bson import ObjectId
            
            # S'assurer que current_user_id est bien une string
            if not isinstance(current_user_id, str):
                current_user_id = str(current_user_id)
            
            users_col = db.users
            
            # Récupérer l'utilisateur
            try:
                user = users_col.find_one({'_id': ObjectId(current_user_id)})
                if user and isinstance(user, dict):
                    user_email = user.get('email', 'unknown')
                else:
                    user_email = 'unknown'
            except Exception as e:
                print(f"Erreur récupération utilisateur: {e}")
                user_email = 'unknown'
            
            data = request.get_json()
            if not data:
                return jsonify({"error": "Données manquantes"}), 400
                
            url = data.get('url') if isinstance(data, dict) else None
            
            if not url:
                return jsonify({"error": "URL manquante"}), 400
            
            # 🗑️ Mise en CORBEILLE (suppression définitive)
            result = liens_collection.update_one(
                {"url": url},
                {"$set": {
                    "en_corbeille": True,
                    "date_corbeille": datetime.now(),
                    "mis_corbeille_par": user_email,
                    "raison_corbeille": data.get('raison', 'Supprimé définitivement'),
                    "ignore_rescrape": True
                }}
            )
            
            if result.modified_count > 0:
                return jsonify({"success": True, "message": "Offre mise en corbeille"})
            else:
                return jsonify({"error": "Offre non trouvée"}), 404
        except Exception as e:
            print(f"Erreur dans supprimer_offre: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/corbeille', methods=['GET'])
    @token_required
    def get_offres_corbeille(current_user_id):
        """Liste des offres en corbeille"""
        try:
            offres = list(liens_collection.find(
                {"en_corbeille": True},
                {"_id": 0}
            ).sort("date_corbeille", -1))
            
            return jsonify(offres)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/masques', methods=['GET'])
    @token_required
    def get_offres_masquees(current_user_id):
        """Liste des offres masquées (exclut corbeille)"""
        try:
            offres = list(liens_collection.find(
                {
                    "$and": [
                        {
                            "$or": [
                                {"est_masque": True},
                                {"masque": True}
                            ]
                        },
                        {
                            "$or": [
                                {"en_corbeille": {"$exists": False}},
                                {"en_corbeille": False},
                                {"en_corbeille": None}
                            ]
                        }
                    ]
                },
                {"_id": 0}
            ).sort("date_masquage", -1))
            
            return jsonify(offres)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    @app.route('/api/offres-ia/sources', methods=['GET'])
    @token_required
    def get_sources_offres(current_user_id):
        """Liste des sources d'appels d'offres"""
        try:
            sources = list(sources_collection.find({}, {"_id": 0}))
            return jsonify(sources)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    
    print("✅ Routes Appels d'Offres IA enregistrées:")
    print("   GET  /api/offres-ia/statistiques")
    print("   GET  /api/offres-ia/informatique")
    print("   POST /api/offres-ia/masquer")
    print("   POST /api/offres-ia/demasquer")
    print("   POST /api/offres-ia/supprimer")
    print("   GET  /api/offres-ia/masques")
    print("   GET  /api/offres-ia/corbeille")
    print("   GET  /api/offres-ia/sources")




