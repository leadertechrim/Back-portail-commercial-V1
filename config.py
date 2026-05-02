import os
from flask import Flask
from flask_cors import CORS
from flask_bcrypt import Bcrypt

def create_app():
    """Crée et configure l'application Flask"""
    app = Flask(__name__)
    
    # Configuration CORS
    CORS(app, origins=['*'], supports_credentials=True)
    
    # Configuration sécurisée
    app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
    
    # Initialisation de Bcrypt
    bcrypt = Bcrypt(app)
    app.bcrypt = bcrypt
    
    return app

