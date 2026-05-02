"""
Script pour créer le premier compte administrateur
Exécuter une seule fois : python create_admin.py
"""
from database import users_col, roles_collection, permissions_collection
from flask_bcrypt import Bcrypt
from datetime import datetime
from crypto_utils import encrypt_password

# ============================================================
# ⚙️  MODIFIER ICI VOS INFORMATIONS ADMIN
# ============================================================
ADMIN_EMAIL    = "admin@aplofr.com"
ADMIN_PASSWORD = "Admin@1234"
ADMIN_NAME     = "Administrateur"
ADMIN_TEL      = "+22600000001"
ADMIN_ADRESSE  = "Dakar"
# ============================================================

bcrypt = Bcrypt()

def init_roles():
    """Créer les rôles par défaut si absents"""
    permissions_data = [
        {"nom": "view_offers",     "description": "Voir les offres",         "category": "Offres"},
        {"nom": "create_offers",   "description": "Créer des offres",        "category": "Offres"},
        {"nom": "edit_offers",     "description": "Modifier les offres",     "category": "Offres"},
        {"nom": "delete_offers",   "description": "Supprimer les offres",    "category": "Offres"},
        {"nom": "view_quotes",     "description": "Voir les devis",          "category": "Devis"},
        {"nom": "create_quotes",   "description": "Créer des devis",         "category": "Devis"},
        {"nom": "edit_quotes",     "description": "Modifier les devis",      "category": "Devis"},
        {"nom": "delete_quotes",   "description": "Supprimer les devis",     "category": "Devis"},
        {"nom": "view_invoices",   "description": "Voir les factures",       "category": "Factures"},
        {"nom": "create_invoices", "description": "Créer des factures",      "category": "Factures"},
        {"nom": "edit_invoices",   "description": "Modifier les factures",   "category": "Factures"},
        {"nom": "delete_invoices", "description": "Supprimer les factures",  "category": "Factures"},
        {"nom": "view_clients",    "description": "Voir les clients",        "category": "Clients"},
        {"nom": "create_clients",  "description": "Créer des clients",       "category": "Clients"},
        {"nom": "edit_clients",    "description": "Modifier les clients",    "category": "Clients"},
        {"nom": "delete_clients",  "description": "Supprimer les clients",   "category": "Clients"},
        {"nom": "view_personnel",  "description": "Voir le personnel",       "category": "Personnel"},
        {"nom": "create_personnel","description": "Créer du personnel",      "category": "Personnel"},
        {"nom": "edit_personnel",  "description": "Modifier le personnel",   "category": "Personnel"},
        {"nom": "delete_personnel","description": "Supprimer le personnel",  "category": "Personnel"},
        {"nom": "view_partners",   "description": "Voir les partenaires",    "category": "Partenaires"},
        {"nom": "create_partners", "description": "Créer des partenaires",   "category": "Partenaires"},
        {"nom": "edit_partners",   "description": "Modifier les partenaires","category": "Partenaires"},
        {"nom": "delete_partners", "description": "Supprimer les partenaires","category": "Partenaires"},
        {"nom": "view_sources",    "description": "Voir les sources",        "category": "Sources"},
        {"nom": "admin_settings",  "description": "Gérer les paramètres",    "category": "Administration"},
        {"nom": "manage_users",    "description": "Gérer les utilisateurs",  "category": "Administration"},
        {"nom": "manage_roles",    "description": "Gérer les rôles",        "category": "Administration"},
        {"nom": "view_analytics",  "description": "Voir les analyses",       "category": "Administration"},
        {"nom": "view_reports",    "description": "Voir les rapports",       "category": "Rapports"},
        {"nom": "export_data",     "description": "Exporter les données",    "category": "Rapports"},
    ]

    # Insérer les permissions manquantes
    for perm in permissions_data:
        if not permissions_collection.find_one({"nom": perm["nom"]}):
            perm["created_at"] = datetime.utcnow()
            permissions_collection.insert_one(perm)

    # Créer le rôle admin si absent
    if not roles_collection.find_one({"nom": "admin"}):
        roles_collection.insert_one({
            "nom": "admin",
            "description": "Administrateur avec tous les droits",
            "couleur": "#dc3545",
            "ordre": 1,
            "permissions": [p["nom"] for p in permissions_data],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        print("✅ Rôle 'admin' créé")
    else:
        print("ℹ️  Rôle 'admin' déjà existant")

    # Créer le rôle user si absent
    if not roles_collection.find_one({"nom": "user"}):
        roles_collection.insert_one({
            "nom": "user",
            "description": "Utilisateur standard",
            "couleur": "#007bff",
            "ordre": 2,
            "permissions": ["view_offers","view_quotes","view_invoices","view_clients","view_reports"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        print("✅ Rôle 'user' créé")

    # Créer le rôle spectateur si absent
    if not roles_collection.find_one({"nom": "spectateur"}):
        roles_collection.insert_one({
            "nom": "spectateur",
            "description": "Lecteur avec accès en lecture seule",
            "couleur": "#6c757d",
            "ordre": 3,
            "permissions": ["view_offers","view_quotes","view_invoices"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
        print("✅ Rôle 'spectateur' créé")


def create_admin():
    """Créer le compte administrateur"""
    # Vérifier si l'admin existe déjà
    existing = users_col.find_one({"email": ADMIN_EMAIL})
    if existing:
        print(f"⚠️  Un utilisateur avec l'email '{ADMIN_EMAIL}' existe déjà.")
        return

    # Hacher le mot de passe
    hashed = bcrypt.generate_password_hash(ADMIN_PASSWORD).decode("utf-8")
    
    try:
        encrypted = encrypt_password(ADMIN_PASSWORD)
    except Exception:
        encrypted = ""

    user = {
        "email": ADMIN_EMAIL,
        "password": hashed,
        "password_encrypted": encrypted,
        "name": ADMIN_NAME,
        "role": "admin",
        "telephone": ADMIN_TEL,
        "whatsapp": ADMIN_TEL,
        "adresse": ADMIN_ADRESSE,
        "statut": "actif",
        "Fonction": "Administrateur Système",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    users_col.insert_one(user)
    print(f"✅ Compte admin créé avec succès !")
    print(f"   📧 Email    : {ADMIN_EMAIL}")
    print(f"   🔑 Password : {ADMIN_PASSWORD}")
    print(f"   👤 Nom      : {ADMIN_NAME}")
    print(f"   🛡️  Rôle     : admin")


if __name__ == "__main__":
    print("=" * 50)
    print("  🚀 Initialisation du compte Administrateur")
    print("=" * 50)
    print("\n[1/2] Vérification des rôles...")
    init_roles()
    print("\n[2/2] Création du compte admin...")
    create_admin()
    print("\n✅ Terminé ! Vous pouvez vous connecter sur le frontend.")
    print("=" * 50)
