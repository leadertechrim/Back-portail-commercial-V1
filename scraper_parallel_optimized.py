"""
SCRAPER PARALLÈLE OPTIMISÉ - ULTRA RAPIDE
Utilise ThreadPoolExecutor pour traiter plusieurs liens en parallèle
Double filtrage IA : BERT + Modèle IA (local ou open source)
Ignore la corbeille automatiquement
"""
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import get_db
import re
import io
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

try:
    import PyPDF2
except:
    print("⚠️ PyPDF2 non installé")
    PyPDF2 = None

# MongoDB
db = get_db()
sources_collection = db["appels_doffres_sources"]
liens_collection = db["appels_doffres_liens"]

# Lock pour éviter les conflits d'écriture MongoDB
mongo_lock = threading.Lock()

# 🔍 ÉTAPE 1 : Modèle pour détecter "Appel d'offres" (BERT général)
print("🔍 Chargement du filtre BERT (détection appels d'offres)...")
try:
    filtre_appel_offres = pipeline(
        "zero-shot-classification",
        model="facebook/bart-large-mnli"
    )
    print("✅ Filtre appels d'offres chargé !")
    USE_FILTRE = True
except:
    print("⚠️ Filtre non disponible, utilisation de mots-clés")
    filtre_appel_offres = None
    USE_FILTRE = False

# 💻 ÉTAPE 2 : Modèle pour détecter "Informatique"
print("💻 Chargement du modèle IA (détection informatique)...")
try:
    model_path = "model_appel_offre_ai"
    if os.path.exists(model_path):
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        classifier_info = pipeline("text-classification", model=model, tokenizer=tokenizer, device=-1)
        print("✅ Modèle local informatique chargé !")
        USE_LOCAL_MODEL = True
        MODEL_TYPE = "local"
    else:
        raise FileNotFoundError("Modèle local non trouvé")
except Exception as e:
    print(f"⚠️ Modèle local non disponible : {e}")
    print("📦 Chargement du modèle open source (Zero-Shot)...")
    try:
        classifier_info = pipeline("zero-shot-classification", model="facebook/bart-large-mnli", device=-1)
        USE_LOCAL_MODEL = False
        MODEL_TYPE = "zero-shot"
        print("✅ Modèle open source chargé")
    except Exception as e2:
        print(f"⚠️ Fallback vers mots-clés : {e2}")
        classifier_info = None
        USE_LOCAL_MODEL = False
        MODEL_TYPE = "keywords"


def est_appel_offres(texte, url):
    """FILTRE 1 : Vérifie si c'est vraiment un appel d'offres"""
    try:
        # Filtrer par URL
        url_lower = url.lower()
        urls_a_ignorer = [
            '/contact', '/a-propos', '/about', '/mentions-legales',
            '/politique', '/confidentialite', '/equipe', '/presentation',
            '/direction', '/mission', '/lois', '/decrets', '/circulaires',
            'facebook.com', 'twitter.com', 'linkedin.com', 'youtube.com',
            '/statistiques', '/rapports', '/documents-types'
        ]
        
        if any(ignore in url_lower for ignore in urls_a_ignorer):
            return False, 0.0, "URL ignorée"
        
        # BERT Zero-shot
        if USE_FILTRE and filtre_appel_offres:
            labels = ["appel d'offres", "page informative", "navigation"]
            result = filtre_appel_offres(texte[:500], labels)
            if result["labels"][0] == "appel d'offres" and result["scores"][0] > 0.5:
                return True, result["scores"][0], "BERT"
        
        # Fallback : mots-clés
        mots_cles_ao = [
            "appel d'offres", "appel d offres", "marché public", "avis d'appel",
            "avis dappel", "consultation", "soumission", "offre technique",
            "cahier des charges", "dossier d'appel", "manifestation d'intérêt"
        ]
        
        texte_lower = texte.lower()
        if any(mot in texte_lower for mot in mots_cles_ao):
            return True, 0.8, "mots-clés"
        
        return False, 0.0, "non détecté"
        
    except Exception as e:
        return False, 0.0, "erreur"


def est_informatique(texte):
    """FILTRE 2 : Vérifie si c'est informatique - Compatible avec tous les types de modèles"""
    try:
        if not texte or len(texte.strip()) < 50:
            return False, 0.0
        
        # Mots-clés informatiques pour fallback
        mots_cles_info = [
            "informatique", "logiciel", "software", "matériel informatique", "hardware",
            "réseau", "serveur", "base de données", "système d'information", "SI",
            "développement", "application", "cloud", "cybersécurité", "sécurité informatique",
            "ERP", "CRM", "infrastructure IT", "data center", "virtualisation",
            "système informatique", "équipement informatique", "maintenance informatique",
            "licence logiciel", "progiciel", "ordinateur", "PC",
            "stockage", "sauvegarde", "backup", "firewall", "pare-feu",
            "wifi", "fibre optique", "câblage réseau", "switch", "routeur"
        ]
        
        texte_lower = texte.lower()
        
        # Si zero-shot classification
        if MODEL_TYPE == "zero-shot" and classifier_info:
            labels = [
                "informatique et technologies",
                "travaux et construction",
                "fournitures de bureau",
                "services généraux"
            ]
            result = classifier_info(texte[:500], labels, multi_label=False)
            
            if result["labels"][0] == "informatique et technologies" and result["scores"][0] > 0.4:
                nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_lower)
                if nb_mots_cles >= 1 or result["scores"][0] > 0.6:
                    return True, result["scores"][0]
            
            # Fallback : mots-clés
            nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_lower)
            if nb_mots_cles >= 3:
                return True, 0.75
            
            return False, 0.0
        
        # Si modèle local
        elif MODEL_TYPE == "local" and classifier_info:
            result = classifier_info(texte[:500])
            label = result[0]["label"]
            score = result[0]["score"]
            est_info = label in ["LABEL_1", "informatique", "IT", "1"] and score > 0.6
            return est_info, score
        
        # Fallback : mots-clés uniquement
        else:
            nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte_lower)
            if nb_mots_cles >= 2:
                return True, min(0.7 + (nb_mots_cles * 0.05), 0.95)
            return False, 0.0
    
    except Exception as e:
        print(f"⚠️ Erreur classification : {str(e)[:40]}")
        # Fallback ultime : mots-clés
        mots_cles_info = ["informatique", "logiciel", "software", "système d'information", "SI", "serveur", "réseau"]
        nb_mots_cles = sum(1 for mot in mots_cles_info if mot in texte.lower())
        if nb_mots_cles >= 2:
            return True, 0.7
        return False, 0.0


def normaliser_url(url, base_url):
    """Convertit URL relative en absolue"""
    if url.startswith("http"):
        return url
    elif url.startswith("/"):
        parts = base_url.split("/")
        return f"{parts[0]}//{parts[2]}{url}"
    else:
        return "/".join(base_url.split("/")[:-1]) + "/" + url


def extraire_pdf_urls(soup, page_url):
    """Extrait PDF (limité à 10)"""
    pdf_urls = []
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith('.pdf'):
            pdf_urls.append({
                "url": normaliser_url(a["href"], page_url),
                "texte": a.get_text().strip() or "PDF"
            })
    return pdf_urls[:10]  # Max 10 PDF


def extraire_texte_pdf(pdf_url):
    """Extrait texte d'un PDF"""
    if not PyPDF2:
        return ""
    try:
        response = requests.get(pdf_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
        if response.status_code != 200:
            return ""
        pdf_file = io.BytesIO(response.content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        texte = ""
        for page in pdf_reader.pages[:3]:  # 3 premières pages
            texte += page.extract_text()
        return texte[:2000]
    except:
        return ""


def analyser_lien_parallele(lien_url, source_info):
    """
    Analyse un lien (utilisé en parallèle)
    Retourne les données ou None
    """
    try:
        # 🗑️ Vérifier corbeille AVANT toute analyse
        with mongo_lock:
            lien_existant = liens_collection.find_one({"url": lien_url})
        
        if lien_existant:
            if lien_existant.get("en_corbeille") or lien_existant.get("ignore_rescrape"):
                return {"status": "corbeille", "url": lien_url}
            return {"status": "existant", "url": lien_url}
        
        # Récupérer la page
        response = requests.get(lien_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Extraire données de base
        titre = soup.find("title")
        titre = titre.get_text().strip() if titre else "Sans titre"
        
        contenu = " ".join([p.get_text().strip() for p in soup.find_all("p")])
        
        meta_desc = soup.find("meta", {"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""
        
        texte_preliminaire = f"{titre} {contenu[:500]} {description}"
        
        # 🔍 FILTRE 1 : Appel d'offres ?
        est_ao, score_ao, methode = est_appel_offres(texte_preliminaire, lien_url)
        
        if not est_ao:
            return {"status": "filtre", "url": lien_url, "raison": methode}
        
        # PDF
        pdf_urls = extraire_pdf_urls(soup, lien_url)
        contenu_pdf = ""
        pdf_analyses = []
        
        if pdf_urls:
            # Analyser 3 premiers PDF max
            for pdf in pdf_urls[:3]:
                texte = extraire_texte_pdf(pdf["url"])
                if texte:
                    contenu_pdf += " " + texte
                    pdf_analyses.append({
                        "url": pdf["url"],
                        "texte": pdf["texte"],
                        "contenu_extrait": True
                    })
        
        texte_complet = f"{titre} {contenu} {contenu_pdf} {description}"
        
        # 💻 FILTRE 2 : Informatique ?
        est_info, score_info = est_informatique(texte_complet)
        
        return {
            "status": "nouveau",
            "url": lien_url,
            "data": {
                "titre": titre,
                "contenu": texte_complet[:2000],
                "contenu_pdf": contenu_pdf[:1000],
                "description": description,
                "longueur_contenu": len(texte_complet),
                "liens_pdf": pdf_urls[:5] if est_info else pdf_urls[:3],
                "nb_pdf": len(pdf_urls),
                "nb_pdf_analyses": len(pdf_analyses),
                "est_appel_offres": est_ao,
                "appel_offres_score": score_ao,
                "est_informatique_ia": est_info,
                "ia_score": score_info,
                "ia_model": MODEL_TYPE,
                "source_entite": source_info.get("nom_entite", ""),
                "source_categorie": source_info.get("categorie", "")
            }
        }
        
    except Exception as e:
        return {"status": "erreur", "url": lien_url, "error": str(e)[:100]}


def main():
    """Scraper parallèle avec ThreadPoolExecutor"""
    print("\n" + "="*70)
    print("⚡ SCRAPER PARALLÈLE OPTIMISÉ - Ultra Rapide")
    print("="*70)
    
    sources = list(sources_collection.find({}))
    
    if not sources:
        print("\n❌ Aucune source trouvée")
        return
    
    print(f"\n📊 {len(sources)} source(s) trouvée(s)")
    print(f"🔧 Workers parallèles : 10")
    print(f"🧠 Double filtrage IA : ACTIVÉ\n")
    
    stats = {
        "total_liens": 0,
        "nouveaux": 0,
        "existants": 0,
        "corbeille": 0,
        "filtres": 0,
        "informatique": 0,
        "erreurs": 0
    }
    
    for idx_source, source in enumerate(sources, 1):
        source_url = source.get("url", "")
        source_nom = source.get("nom_entite", "Sans nom")
        
        print(f"\n{'='*70}")
        print(f"[{idx_source}/{len(sources)}] 🔍 {source_nom}")
        print(f"{'='*70}")
        print(f"   🌐 {source_url}")
        
        # Extraire liens
        print(f"\n   📡 Extraction des liens...")
        try:
            response = requests.get(source_url, timeout=10, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
            })
            soup = BeautifulSoup(response.text, "html.parser")
            
            liens = []
            for a in soup.find_all("a", href=True):
                href = normaliser_url(a["href"], source_url)
                if href.startswith("http"):
                    liens.append(href)
            
            liens = list(set(liens))[-100:]  # 100 derniers, uniques
            
        except Exception as e:
            print(f"   ❌ Erreur extraction : {e}")
            continue
        
        stats["total_liens"] += len(liens)
        print(f"   ✅ {len(liens)} lien(s) à analyser")
        
        # ⚡ TRAITEMENT PARALLÈLE avec 10 workers
        print(f"\n   ⚡ Traitement parallèle (10 workers)...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Soumettre tous les liens en parallèle
            futures = {
                executor.submit(analyser_lien_parallele, lien, source): lien 
                for lien in liens
            }
            
            # Traiter les résultats au fur et à mesure
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=30)
                    status = result.get("status")
                    
                    if status == "corbeille":
                        stats["corbeille"] += 1
                        if idx % 10 == 0:
                            print(f"   [{idx}/{len(liens)}] 🗑️ Corbeille")
                    
                    elif status == "existant":
                        stats["existants"] += 1
                        if idx % 10 == 0:
                            print(f"   [{idx}/{len(liens)}] ⏭️ Existant")
                    
                    elif status == "filtre":
                        stats["filtres"] += 1
                        if idx % 10 == 0:
                            print(f"   [{idx}/{len(liens)}] ⏭️ Filtré")
                    
                    elif status == "nouveau":
                        data = result["data"]
                        
                        # Insérer en BD (avec lock)
                        lien_doc = {
                            "url": result["url"],
                            "source_url": source_url,
                            "source_entite": data["source_entite"],
                            "source_categorie": data["source_categorie"],
                            "date_added": datetime.now(),
                            "titre": data["titre"],
                            "contenu": data["contenu"],
                            "contenu_pdf": data["contenu_pdf"],
                            "description": data["description"],
                            "longueur_contenu": data["longueur_contenu"],
                            "liens_pdf": data["liens_pdf"],
                            "nb_pdf": data["nb_pdf"],
                            "nb_pdf_analyses": data["nb_pdf_analyses"],
                            "est_appel_offres": data["est_appel_offres"],
                            "appel_offres_score": data["appel_offres_score"],
                            "est_informatique_ia": data["est_informatique_ia"],
                            "ia_score": data["ia_score"],
                            "ia_model": data["ia_model"],
                            "is_processed_by_model": True,
                            "analysis_result": {
                                "est_informatique_ia": data["est_informatique_ia"],
                                "score": data["ia_score"],
                                "model": data["ia_model"],
                                "date_analyse": datetime.now()
                            }
                        }
                        
                        with mongo_lock:
                            liens_collection.insert_one(lien_doc)
                        
                        stats["nouveaux"] += 1
                        if data["est_informatique_ia"]:
                            stats["informatique"] += 1
                            print(f"   [{idx}/{len(liens)}] ✅ INFORMATIQUE ! (score: {data['ia_score']:.0%})")
                        else:
                            if idx % 10 == 0:
                                print(f"   [{idx}/{len(liens)}] ✅ Ajouté (non info)")
                    
                    elif status == "erreur":
                        stats["erreurs"] += 1
                    
                except Exception as e:
                    stats["erreurs"] += 1
        
        print(f"\n   📊 Source terminée : {stats['nouveaux']} nouveaux")
    
    # Résumé final
    print(f"\n{'='*70}")
    print(f"⚡ SCRAPING PARALLÈLE TERMINÉ")
    print(f"{'='*70}")
    print(f"📊 Statistiques globales :")
    print(f"   - Total liens analysés  : {stats['total_liens']}")
    print(f"   - 🆕 Nouveaux ajoutés    : {stats['nouveaux']}")
    print(f"   - 💻 Informatique        : {stats['informatique']}")
    print(f"   - ⏭️  Déjà existants      : {stats['existants']}")
    print(f"   - 🗑️  En corbeille        : {stats['corbeille']}")
    print(f"   - ⏭️  Filtrés (pas AO)    : {stats['filtres']}")
    print(f"   - ❌ Erreurs             : {stats['erreurs']}")
    
    if stats['total_liens'] > 0:
        efficacite = (stats['filtres'] + stats['corbeille']) / stats['total_liens'] * 100
        print(f"\n💡 Efficacité filtrage : {efficacite:.1f}% de liens inutiles évités !")
    
    print(f"\n⚡ Traitement parallèle : ~3-5x plus rapide que séquentiel")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()


