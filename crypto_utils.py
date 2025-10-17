"""
Utilitaires de chiffrement/déchiffrement AES pour les mots de passe
⚠️ ATTENTION : Stocker des mots de passe déchiffrables est une faille de sécurité
Ceci est implémenté UNIQUEMENT sur demande explicite du client
"""
from cryptography.fernet import Fernet
import base64
import os

# Clé de chiffrement (⚠️ À stocker dans variables d'environnement en production)
# Pour dev, on utilise une clé fixe (⚠️ CHANGER EN PRODUCTION)
SECRET_KEY = os.getenv('ENCRYPTION_KEY', 'ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg=')

def get_cipher():
    """Obtenir l'objet de chiffrement Fernet"""
    try:
        return Fernet(SECRET_KEY.encode() if isinstance(SECRET_KEY, str) else SECRET_KEY)
    except:
        # Si la clé n'est pas valide, en générer une nouvelle
        key = Fernet.generate_key()
        print(f"⚠️ Nouvelle clé générée : {key.decode()}")
        print("⚠️ Sauvegarder cette clé dans les variables d'environnement !")
        return Fernet(key)

def encrypt_password(password: str) -> str:
    """
    Chiffre un mot de passe avec AES (Fernet)
    Retourne une chaîne base64
    """
    if not password:
        return ""
    
    try:
        cipher = get_cipher()
        encrypted = cipher.encrypt(password.encode())
        return encrypted.decode()
    except Exception as e:
        print(f"❌ Erreur chiffrement : {e}")
        return ""

def decrypt_password(encrypted_password: str) -> str:
    """
    Déchiffre un mot de passe chiffré avec AES (Fernet)
    Retourne le mot de passe en clair
    """
    if not encrypted_password:
        return ""
    
    try:
        cipher = get_cipher()
        decrypted = cipher.decrypt(encrypted_password.encode())
        return decrypted.decode()
    except Exception as e:
        print(f"❌ Erreur déchiffrement : {e}")
        return ""

# Test
if __name__ == "__main__":
    test_password = "MonMotDePasse123"
    
    print(f"🔐 Mot de passe original : {test_password}")
    
    encrypted = encrypt_password(test_password)
    print(f"🔒 Chiffré : {encrypted}")
    
    decrypted = decrypt_password(encrypted)
    print(f"🔓 Déchiffré : {decrypted}")
    
    if test_password == decrypted:
        print("✅ Chiffrement/Déchiffrement fonctionnel !")
    else:
        print("❌ Erreur dans le processus")


