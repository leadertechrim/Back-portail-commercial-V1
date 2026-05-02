"""
Scraper continu pour traitement en temps réel avec OpenRouter
Lance le scraper toutes les X minutes
"""
import time
from datetime import datetime
import os

# Choisir quel scraper utiliser
USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'true').lower() == 'true'

if USE_OPENROUTER:
    print("🤖 Utilisation du scraper avec OpenRouter AI")
    from scraper_openrouter import main as scraper_main
else:
    print("⚡ Utilisation du scraper avec scoring rapide")
    from scraper_smart_filter_improved import main as scraper_main

# Configuration
INTERVAL_MINUTES = int(os.getenv('SCRAPER_INTERVAL_MINUTES', 30))
MAX_ERRORS = int(os.getenv('SCRAPER_MAX_ERRORS', 5))

def log(message):
    """Log avec timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)

def run_continuous_scraper():
    """Lance le scraper en boucle continue"""
    log("="*70)
    log("🚀 SCRAPER CONTINU - Démarrage")
    log(f"⏰ Intervalle: {INTERVAL_MINUTES} minutes")
    log(f"🤖 OpenRouter: {USE_OPENROUTER}")
    log("="*70)
    
    error_count = 0
    iteration = 0
    
    while True:
        iteration += 1
        log(f"\n{'='*70}")
        log(f"🔄 ITÉRATION #{iteration}")
        log(f"{'='*70}")
        
        try:
            # Lancer le scraper
            log("🏃 Lancement du scraper...")
            scraper_main()
            log("✅ Scraping terminé avec succès")
            error_count = 0  # Réinitialiser
            
        except KeyboardInterrupt:
            log("\n⚠️ Arrêt demandé par l'utilisateur")
            break
            
        except Exception as e:
            error_count += 1
            log(f"❌ Erreur durant le scraping: {str(e)[:100]}")
            log(f"⚠️ Nombre d'erreurs consécutives: {error_count}/{MAX_ERRORS}")
            
            if error_count >= MAX_ERRORS:
                log(f"🛑 Arrêt après {MAX_ERRORS} erreurs consécutives")
                break
        
        # Attendre avant la prochaine itération
        next_run = datetime.now().replace(second=0, microsecond=0)
        log(f"\n⏸️ Pause de {INTERVAL_MINUTES} minutes...")
        log(f"⏰ Prochain scraping prévu vers: {next_run}")
        
        time.sleep(INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    run_continuous_scraper()

