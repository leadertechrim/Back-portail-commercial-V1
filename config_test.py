# Configuration pour les tests des routes offres
# Modifiez ces valeurs selon votre environnement

# URL du serveur
BASE_URL = "http://localhost:8000"

# Credentials de test
TEST_CREDENTIALS = {
    "email": "admin@test.com",      # Remplacez par votre email
    "password": "admin123"          # Remplacez par votre mot de passe
}

# Données de test pour les offres
TEST_OFFRE_DATA = {
    "intitulee": "Test Debug Offre",
    "lien": "https://example.com/test-debug",
    "client": "Client Test Debug",
    "date_limite": "2025-12-31T23:59:59.000Z",
    "statut": "Non préparé",
    "note_commentaire": "Offre de test pour diagnostiquer le problème des champs",
    "documents": [],
    # NOUVEAUX CHAMPS À TESTER
    "Catégorie": "national",
    "N-Offre": "DEBUG-001",
    "Partenaire": "Partenaire Debug Test"
}

# Données de mise à jour pour les tests
TEST_UPDATE_DATA = {
    "Catégorie": "international",
    "N-Offre": "DEBUG-002-UPDATED",
    "Partenaire": "Partenaire Mis à Jour",
    "note_commentaire": "Offre mise à jour pour test debug"
}

# Options de test
TEST_OPTIONS = {
    "verbose": True,              # Afficher tous les détails
    "test_creation": True,        # Tester la création
    "test_retrieval": True,       # Tester la récupération
    "test_update": True,          # Tester la mise à jour
    "test_debug": True,           # Tester la route debug
    "test_my_offres": True        # Tester les offres personnelles
}


