"""
SCRAPER AVEC AFFICHAGE INSTANTANÉ
1. Collecte les liens RAPIDEMENT
2. Ajoute en base IMMÉDIATEMENT (statut: en_attente_analyse)
3. Analyse IA EN ARRIÈRE-PLAN
4. Met à jour le statut après analyse
"""
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import get_db
import re
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import PyPDF2
except:
    PyPDF2 = None

# MongoDB
db = get_db()
sources_collection = db["appels_doffres_sources"]
liens_collection = db["appels_doffres_liens"]

# Lock MongoDB
mongo_lock = threading.Lock()

# Chargement des modèles IA (une seule fois)
print("🔍 Chargement des modèles IA...")
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
    
    # BERT pour détecter appels d'offres
    filtre_appel_offres = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    USE_FILTRE = True
    print("✅ Filtre BERT chargé")
    
    # Modèle pour détecter informatique
    model_path = "model_appel_offre_ai"
    if os.path.exists(model_path):
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        classifier_info = pipeline("text-classification", model=model, tokenizer=tokenizer, device=-1)
        USE_LOCAL_MODEL = True
        MODEL_TYPE = "local"
        print("✅ Modèle local informatique chargé")
    else:
        # Utiliser zero-shot pour l'informatique aussi
        classifier_info = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
        USE_LOCAL_MODEL = False
        MODEL_TYPE = "zero-shot"
        print("✅ Modèle open source chargé (zero-shot classification)")
except Exception as e:
    print(f"⚠️ Modèles IA non disponibles : {e}")
    filtre_appel_offres = None
    classifier_info = None
    USE_FILTRE = False
    USE_LOCAL_MODEL = False
    MODEL_TYPE = "keywords"


def normaliser_url(url, base_url):
    """Convertit URL relative en absolue"""
    if url.startswith("http"):
        return url
    elif url.startswith("/"):
        parts = base_url.split("/")
        return f"{parts[0]}//{parts[2]}{url}"
    else:
        return "/".join(base_url.split("/")[:-1]) + "/" + url


def extraire_liens_rapide(source_url):
    """Extraire les liens d'une source RAPIDEMENT (sans analyse)"""
    try:
        response = requests.get(source_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
        })
        soup = BeautifulSoup(response.text, "html.parser")
        
        liens = []
        for a in soup.find_all("a", href=True):
            href = normaliser_url(a["href"], source_url)
            if href.startswith("http") and href != source_url:
                titre_approx = a.get_text().strip() or "Sans titre"
                liens.append({
                    "url": href,
                    "titre_approx": titre_approx[:200]
                })
        
        # Dédupliquer et limiter
        urls_vues = set()
        liens_uniques = []
        for lien in liens:
            if lien["url"] not in urls_vues:
                urls_vues.add(lien["url"])
                liens_uniques.append(lien)
        
        return liens_uniques[-100:]  # 100 derniers
        
    except Exception as e:
        print(f"   ❌ Erreur extraction : {e}")
        return []


def ajouter_lien_en_attente(lien_data, source_info):
    """Ajoute un lien en base IMMÉDIATEMENT (avant analyse)"""
    try:
        # Vérifier si existe ou en corbeille
        with mongo_lock:
            existant = liens_collection.find_one({"url": lien_data["url"]})
        
        if existant:
            if existant.get("en_corbeille") or existant.get("ignore_rescrape"):
                return "corbeille"
            return "existant"
        
        # Ajouter IMMÉDIATEMENT avec statut "en_attente_analyse"
        lien_doc = {
            "url": lien_data["url"],
            "source_url": source_info["url"],
            "source_entite": source_info.get("nom_entite", ""),
            "source_categorie": source_info.get("categorie", ""),
            "date_added": datetime.now(),
            "titre": lien_data["titre_approx"],
            "statut_analyse": "en_attente",  # 🆕 En attente d'analyse
            "est_appel_offres": None,  # Sera mis à jour après analyse
            "analysis_result": {
                "est_informatique_ia": None,
                "en_cours": True
            }
        }
        
        with mongo_lock:
            result = liens_collection.insert_one(lien_doc)
        
        return str(result.inserted_id)
        
    except Exception as e:
        print(f"   ❌ Erreur ajout : {e}")
        return None


def analyser_lien_background(lien_id, lien_url):
    """Analyse un lien en arrière-plan et met à jour le statut"""
    try:
        # Récupérer la page
        response = requests.get(lien_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraire données
        titre = soup.find("title")
        titre = titre.get_text().strip() if titre else "Sans titre"
        
        contenu = " ".join([p.get_text().strip() for p in soup.find_all("p")])[:2000]
        
        meta_desc = soup.find("meta", {"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""
        
        # PDF
        pdf_urls = []
        for a in soup.find_all("a", href=True):
            if a["href"].lower().endswith('.pdf'):
                pdf_urls.append({
                    "url": normaliser_url(a["href"], lien_url),
                    "texte": a.get_text().strip() or "PDF"
                })
        pdf_urls = pdf_urls[:10]
        
        # Filtre 1 : Appel d'offres ?
        texte_preliminaire = f"{titre} {contenu[:500]} {description}"
        est_ao = False
        score_ao = 0.0
        
        if USE_FILTRE and filtre_appel_offres:
            labels = ["appel d'offres", "page informative", "navigation"]
            result = filtre_appel_offres(texte_preliminaire[:500], labels)
            if result["labels"][0] == "appel d'offres" and result["scores"][0] > 0.5:
                est_ao = True
                score_ao = result["scores"][0]
        else:
            # Mots-clés fallback
            mots_cles = ["appel d'offres", "marché public", "avis d'appel", "consultation"]
            if any(mot in texte_preliminaire.lower() for mot in mots_cles):
                est_ao = True
                score_ao = 0.8
        
        # Filtre 2 : Informatique ?
        est_info = False
        score_info = 0.0
        
        if est_ao and classifier_info:
            texte_complet = f"{titre} {contenu}"
            
            # Mots-clés informatiques
            mots_cles_info = [
                "informatique", "logiciel", "software", "matériel informatique",
                "réseau", "serveur", "base de données", "système d'information", "SI",
                "ERP", "CRM", "cloud", "cybersécurité", "ordinateur", "PC"
            ]
            
            if MODEL_TYPE == "zero-shot":
                # Zero-shot classification
                labels = ["informatique et technologies", "travaux et construction", 
                         "fournitures de bureau", "services généraux"]
                result = classifier_info(texte_complet[:500], labels, multi_label=False)
                
                if result["labels"][0] == "informatique et technologies" and result["scores"][0] > 0.4:
                    nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_complet.lower())
                    if nb_mots_cles >= 1 or result["scores"][0] > 0.6:
                        est_info = True
                        score_info = result["scores"][0]
                else:
                    # Fallback mots-clés
                    nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_complet.lower())
                    if nb_mots_cles >= 3:
                        est_info = True
                        score_info = 0.75
            
            elif MODEL_TYPE == "local":
                # Modèle local
                result = classifier_info(texte_complet[:500])
                label = result[0]["label"]
                score = result[0]["score"]
                est_info = label in ["LABEL_1", "informatique", "IT", "1"] and score > 0.6
                score_info = score
            
            else:
                # Mots-clés uniquement
                nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_complet.lower())
                if nb_mots_cles >= 2:
                    est_info = True
                    score_info = 0.7
        
        # Mettre à jour le lien en base
        update_data = {
            "titre": titre,
            "contenu": contenu,
            "description": description,
            "longueur_contenu": len(contenu),
            "liens_pdf": pdf_urls,
            "nb_pdf": len(pdf_urls),
            "est_appel_offres": est_ao,
            "appel_offres_score": score_ao,
            "statut_analyse": "termine",  # 🆕 Analyse terminée
            "analysis_result": {
                "est_informatique_ia": est_info,
                "score": score_info,
                "model": MODEL_TYPE,
                "date_analyse": datetime.now(),
                "en_cours": False
            },
            "is_processed_by_model": True
        }
        
        with mongo_lock:
            liens_collection.update_one(
                {"_id": lien_id},
                {"$set": update_data}
            )
        
        return {"est_informatique": est_info, "score": score_info}
        
    except Exception as e:
        # Marquer comme erreur
        with mongo_lock:
            liens_collection.update_one(
                {"_id": lien_id},
                {"$set": {
                    "statut_analyse": "erreur",
                    "erreur_analyse": str(e)[:200],
                    "analysis_result.en_cours": False
                }}
            )
        return {"erreur": str(e)}


def main():
    """Scraper avec affichage instantané"""
    print("\n" + "="*70)
    print("⚡ SCRAPER AVEC AFFICHAGE INSTANTANÉ")
    print("="*70)
    print("📊 Étape 1 : Collecte rapide des liens")
    print("📊 Étape 2 : Ajout immédiat en base (visible sur dashboard)")
    print("📊 Étape 3 : Analyse IA en arrière-plan")
    print("="*70 + "\n")
    
    sources = list(sources_collection.find({}))
    
    if not sources:
        print("❌ Aucune source trouvée")
        return
    
    print(f"📊 {len(sources)} source(s) à traiter\n")
    
    stats = {
        "total_liens": 0,
        "nouveaux": 0,
        "existants": 0,
        "corbeille": 0,
        "en_attente_analyse": 0,
        "informatique": 0
    }
    
    liens_a_analyser = []  # Liste des liens à analyser en background
    
    # PHASE 1 : COLLECTE RAPIDE
    print("="*70)
    print("PHASE 1 : COLLECTE RAPIDE DES LIENS")
    print("="*70 + "\n")
    
    for idx_source, source in enumerate(sources, 1):
        source_url = source.get("url", "")
        source_nom = source.get("nom_entite", "Sans nom")
        
        print(f"[{idx_source}/{len(sources)}] 🔍 {source_nom}")
        print(f"   {source_url}")
        
        # Extraire les liens (rapide)
        liens = extraire_liens_rapide(source_url)
        stats["total_liens"] += len(liens)
        
        print(f"   ✅ {len(liens)} lien(s) trouvé(s)")
        
        # Ajouter en base IMMÉDIATEMENT
        for lien in liens:
            result = ajouter_lien_en_attente(lien, source)
            
            if result == "corbeille":
                stats["corbeille"] += 1
            elif result == "existant":
                stats["existants"] += 1
            elif result:  # ID du lien ajouté
                stats["nouveaux"] += 1
                stats["en_attente_analyse"] += 1
                liens_a_analyser.append((result, lien["url"]))
        
        print(f"   📊 Nouveaux: {stats['nouveaux']} | En attente: {stats['en_attente_analyse']}\n")
    
    print("="*70)
    print(f"✅ PHASE 1 TERMINÉE")
    print(f"📊 {stats['nouveaux']} nouveaux liens ajoutés en base")
    print(f"📊 Visibles IMMÉDIATEMENT sur le dashboard !")
    print("="*70 + "\n")
    
    # PHASE 2 : ANALYSE IA EN BACKGROUND
    print("="*70)
    print("PHASE 2 : ANALYSE IA EN ARRIÈRE-PLAN")
    print("="*70)
    print(f"📊 {len(liens_a_analyser)} lien(s) à analyser")
    print("⚡ Traitement parallèle avec 5 workers\n")
    
    if liens_a_analyser:
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(analyser_lien_background, lien_id, lien_url): (lien_id, lien_url)
                for lien_id, lien_url in liens_a_analyser
            }
            
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=60)
                    
                    if result.get("est_informatique"):
                        stats["informatique"] += 1
                        print(f"   [{idx}/{len(liens_a_analyser)}] ✅ INFORMATIQUE (score: {result['score']:.0%})")
                    else:
                        if idx % 10 == 0:
                            print(f"   [{idx}/{len(liens_a_analyser)}] ⏭️ Analysé")
                    
                except Exception as e:
                    print(f"   [{idx}/{len(liens_a_analyser)}] ❌ Erreur")
    
    print("\n" + "="*70)
    print("✅ SCRAPING COMPLET TERMINÉ")
    print("="*70)
    print(f"📊 Statistiques finales :")
    print(f"   - Total liens scannés    : {stats['total_liens']}")
    print(f"   - 🆕 Nouveaux ajoutés     : {stats['nouveaux']}")
    print(f"   - 💻 Informatique détectés: {stats['informatique']}")
    print(f"   - ⏭️  Déjà existants       : {stats['existants']}")
    print(f"   - 🗑️  En corbeille         : {stats['corbeille']}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()


