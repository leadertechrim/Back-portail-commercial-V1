"""Lance Flask + Scraper en parallele pour Docker/Railway"""
import subprocess
import os
import sys
import time

print("=" * 70)
print("🚀 DEMARRAGE : Backend Flask + Scraper Continu")
print("=" * 70)

# Configuration Flask
os.environ['FLASK_APP'] = 'app.py'  # Définir l'application Flask
port = os.getenv('PORT', '8080')
flask_debug = os.getenv('FLASK_DEBUG', 'false').lower()

# 1. Lancer Flask en arrière-plan
print(f"\n[1/2] Lancement Flask sur port {port}...")
print(f"   • FLASK_APP: app.py")
print(f"   • FLASK_DEBUG: {flask_debug}")
flask_cmd = [
    sys.executable, '-m', 'flask', 'run',
    '--host=0.0.0.0',
    f'--port={port}',
    '--no-debugger' if flask_debug != 'true' else '',
    '--no-reload' if flask_debug != 'true' else ''
]
# Filtrer les chaînes vides
flask_cmd = [cmd for cmd in flask_cmd if cmd]
flask_process = subprocess.Popen(flask_cmd, env=os.environ.copy())

# Attendre que Flask démarre
time.sleep(5)
print("✅ Flask demarre")

# 2. Lancer le scraper en arrière-plan
print("\n[2/2] Lancement Scraper continu...")
scraper_cmd = [sys.executable, 'scraper_continuous.py']
scraper_process = subprocess.Popen(scraper_cmd)
print("✅ Scraper demarre")

print("\n" + "=" * 70)
print("✅ TOUT EST LANCE - Services en cours d'execution")
print(f"   • Flask API: http://0.0.0.0:{port}")
print(f"   • Scraper: En boucle continue")
print("=" * 70)

# Garder le processus actif
try:
    while True:
        # Vérifier si Flask est toujours actif
        if flask_process.poll() is not None:
            print("⚠️ Flask s'est arrêté, redémarrage...")
            flask_process = subprocess.Popen(flask_cmd)
        
        # Vérifier si le scraper est toujours actif
        if scraper_process.poll() is not None:
            print("⚠️ Scraper s'est arrêté, redémarrage...")
            scraper_process = subprocess.Popen(scraper_cmd)
        
        time.sleep(30)  # Vérifier toutes les 30 secondes
        
except KeyboardInterrupt:
    print("\n⚠️ Arrêt des services...")
    flask_process.terminate()
    scraper_process.terminate()
    print("✅ Services arrêtés")

