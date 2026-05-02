"""Routes de debug et diagnostic"""
from flask import Blueprint, jsonify
from flask import current_app
from database import client, users_col, sources_col, MONGO_URI
import os

debug_bp = Blueprint('debug', __name__)


@debug_bp.route("/api/debug", methods=["GET"])
def debug_info():
    """Route de diagnostic pour Railway"""
    try:
        # Test de connexion MongoDB
        client.admin.command('ping')
        mongo_status = "Connected"
    except Exception as e:
        mongo_status = "Error: Connection failed"
    
    try:
        # Compter les utilisateurs
        user_count = users_col.count_documents({})
        users_status = f"Found {user_count} users"
    except Exception as e:
        users_status = "Error: Query failed"
    
    try:
        # Compter les sources
        sources_count = sources_col.count_documents({})
        sources_status = f"Found {sources_count} sources"
    except Exception as e:
        sources_status = "Error: Query failed"
    
    return jsonify({
        "status": "Debug Info",
        "mongo_uri": MONGO_URI[:50] + "..." if len(MONGO_URI) > 50 else MONGO_URI,
        "mongo_status": mongo_status,
        "users_status": users_status,
        "sources_status": sources_status,
        "jwt_secret_set": bool(current_app.config["SECRET_KEY"]),
        "environment": {
            "PORT": os.getenv("PORT", "Not set"),
            "JWT_SECRET": "Set" if os.getenv("JWT_SECRET") else "Not set",
            "MONGO_URI": "Set" if os.getenv("MONGO_URI") else "Not set"
        }
    })












