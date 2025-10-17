"""
Scraper INTELLIGENT avec double filtrage IA :
1. BERT vérifie d'abord si c'est un APPEL D'OFFRES
2. Modèle IA (local ou open source) vérifie ensuite si c'est INFORMATIQUE

Cela évite d'analyser des liens inutiles (contact, à propos, etc.)
"""
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from db import get_db
import re
import io
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

try:
    import PyPDF2
except:
    print("⚠️ PyPDF2 non installé")
    PyPDF2 = None

# MongoDB
db = get_db()
sources_collection = db["appels_doffres_sources"]
liens_collection = db["appels_doffres_liens"]

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
    # Essayer d'abord le modèle local s'il existe
    model_path = "model_appel_offre_ai"
    if os.path.exists(model_path):
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        model = AutoModelForSequenceClassification.from_pretrained(model_path)
        classifier_info = pipeline("text-classification", model=model, tokenizer=tokenizer, device=-1)
        print("✅ Modèle local informatique chargé !")
        USE_LOCAL_MODEL = True
        MODEL_TYPE = "local"
    else:
        raise FileNotFoundError("Modèle local non trouvé, utilisation du modèle open source")
except Exception as e:
    print(f"⚠️ Modèle local non disponible : {e}")
    print("📦 Chargement du modèle open source (Zero-Shot Classification)...")
    try:
        # Utiliser un modèle zero-shot multilingue plus performant
        classifier_info = pipeline(
            "zero-shot-classification",
            model="facebook/bart-large-mnli",
            device=-1
        )
        USE_LOCAL_MODEL = False
        MODEL_TYPE = "zero-shot"
        print("✅ Modèle open source chargé (zero-shot classification)")
    except Exception as e2:
        print(f"⚠️ Fallback vers modèle basique : {e2}")
        classifier_info = pipeline("text-classification", model="bert-base-multilingual-cased")
        USE_LOCAL_MODEL = False
        MODEL_TYPE = "bert-basic"


def est_appel_offres(texte, url):
    """
    FILTRE 1 : Vérifie si c'est vraiment un appel d'offres
    Utilise BERT zero-shot OU mots-clés
    """
    try:
        # Filtrer par URL (liens évidents à ignorer)
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
        
        # BERT Zero-shot classification
        if USE_FILTRE and filtre_appel_offres:
            labels = ["appel d'offres", "page informative", "navigation"]
            result = filtre_appel_offres(texte[:500], labels)
            
            # Si "appel d'offres" est le label principal avec score > 0.5
            if result["labels"][0] == "appel d'offres" and result["scores"][0] > 0.5:
                return True, result["scores"][0], "BERT"
        
        # Fallback : mots-clés
        mots_cles_ao = [
            "appel d'offres", "appel d offres", "marché public", "avis d'appel",
            "avis dappel", "consultation", "soumission", "offre technique",
            "cahier des charges", "dossier d'appel", "manifestation d'intérêt",
            "appel à candidature", "demande de prix", "tender", "bid"
        ]
        
        texte_lower = texte.lower()
        if any(mot in texte_lower for mot in mots_cles_ao):
            return True, 0.8, "mots-clés"
        
        return False, 0.0, "non détecté"
        
    except Exception as e:
        print(f"            ⚠️ Erreur filtre : {str(e)[:40]}")
        return False, 0.0, "erreur"


def est_informatique(texte):
    """
    FILTRE 2 : Vérifie si c'est informatique
    Compatible avec modèle local, zero-shot ou mots-clés
    """
    try:
        if not texte or len(texte.strip()) < 50:
            return False, 0.0
        
        # Mots-clés informatiques pour fallback ou renforcement
        mots_cles_informatique = [
            "informatique", "logiciel", "software", "matériel informatique", "hardware",
            "réseau", "serveur", "base de données", "système d'information", "SI",
            "développement", "application", "cloud", "cybersécurité", "sécurité informatique",
            "ERP", "CRM", "infrastructure IT", "data center", "virtualisation",
            "système informatique", "équipement informatique", "maintenance informatique",
            "licence logiciel", "progiciel", "ordinateur", "PC", "serveur",
            "stockage", "sauvegarde", "backup", "firewall", "pare-feu",
            "wifi", "fibre optique", "câblage réseau", "switch", "routeur"
        ]
        
        texte_lower = texte.lower()
        
        # Si zero-shot classification
        if MODEL_TYPE == "zero-shot":
            labels = [
                "informatique et technologies",
                "travaux et construction",
                "fournitures de bureau",
                "services généraux"
            ]
            result = classifier_info(texte[:500], labels, multi_label=False)
            
            # Si "informatique" est le label principal avec un bon score
            if result["labels"][0] == "informatique et technologies" and result["scores"][0] > 0.4:
                # Double vérification avec mots-clés pour renforcer
                nb_mots_cles = sum(1 for mot in mots_cles_informatique if mot in texte_lower)
                if nb_mots_cles >= 1 or result["scores"][0] > 0.6:
                    return True, result["scores"][0]
            
            # Fallback : si beaucoup de mots-clés même avec score faible
            nb_mots_cles = sum(1 for mot in mots_cles_informatique if mot in texte_lower)
            if nb_mots_cles >= 3:
                return True, 0.75
            
            return False, result["scores"][0] if result["labels"][0] == "informatique et technologies" else 0.0
        
        # Si modèle local
        elif MODEL_TYPE == "local":
            result = classifier_info(texte[:500])
            label = result[0]["label"]
            score = result[0]["score"]
            
            # Adapter selon votre modèle
            est_info = label in ["LABEL_1", "informatique", "IT", "1"] and score > 0.6
            
            return est_info, score
        
        # Si modèle basique (bert) - utiliser uniquement mots-clés
        else:
            nb_mots_cles = sum(1 for mot in mots_cles_informatique if mot in texte_lower)
            if nb_mots_cles >= 2:
                return True, min(0.7 + (nb_mots_cles * 0.05), 0.95)
            
            return False, 0.0
    
    except Exception as e:
        print(f"            ⚠️ Erreur classification informatique : {str(e)[:40]}")
        # Fallback ultime : mots-clés
        mots_cles_informatique = ["informatique", "logiciel", "software", "système d'information", "SI", "serveur", "réseau"]
        nb_mots_cles = sum(1 for mot in mots_cles_informatique if mot in texte.lower())
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


def extraire_liens_de_source(url):
    """Extrait tous les liens d'une page source"""
    try:
        response = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        soup = BeautifulSoup(response.text, "html.parser")
        
        liens = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            href = normaliser_url(href, url)
            if href.startswith("http"):
                liens.append(href)
        
        return list(set(liens))
    except Exception as e:
        print(f"      ❌ Erreur : {str(e)[:50]}")
        return []


def extraire_pdf_urls(soup, page_url):
    """Extrait PDF (limité à 10 derniers)"""
    pdf_urls = []
    
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith('.pdf'):
            pdf_urls.append({
                "url": normaliser_url(a["href"], page_url),
                "texte": a.get_text().strip() or "PDF"
            })
    
    for iframe in soup.find_all("iframe"):
        src = iframe.get("src", "")
        if "docs.google.com/gview" in src:
            match = re.search(r'url=(https?://[^&]+\.pdf)', src)
            if match:
                pdf_urls.append({"url": match.group(1), "texte": "PDF"})
    
    # 🆕 LIMITER à 10 derniers PDF (les plus récents)
    if len(pdf_urls) > 10:
        pdf_urls = pdf_urls[-10:]
    
    return pdf_urls


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
        for page in pdf_reader.pages[:5]:
            texte += page.extract_text()
        return texte[:3000]
    except:
        return ""


def analyser_lien_intelligent(url, source_info):
    """
    Analyse intelligente en 2 étapes :
    1. Vérifie si c'est un appel d'offres
    2. Si oui, vérifie si c'est informatique
    """
    try:
        response = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Titre
        titre = soup.find("title")
        titre = titre.get_text().strip() if titre else "Sans titre"
        
        # Contenu
        contenu = " ".join([p.get_text().strip() for p in soup.find_all("p")])
        
        # Description
        meta_desc = soup.find("meta", {"name": "description"})
        description = meta_desc.get("content", "") if meta_desc else ""
        
        # Texte préliminaire pour filtre
        texte_preliminaire = f"{titre} {contenu[:500]} {description}"
        
        # 🔍 ÉTAPE 1 : Vérifier si c'est un appel d'offres
        print(f"         🔍 Filtre appel d'offres...")
        est_ao, score_ao, methode = est_appel_offres(texte_preliminaire, url)
        
        if not est_ao:
            print(f"         ⏭️  Pas un appel d'offres ({methode})")
            return None
        
        print(f"         ✅ Appel d'offres confirmé (score: {score_ao:.2%}, {methode})")
        
        # Continuer l'analyse complète
        # PDF
        pdf_urls = extraire_pdf_urls(soup, url)
        contenu_pdf = ""
        pdf_analyses = []
        
        if pdf_urls:
            print(f"         📄 {len(pdf_urls)} PDF trouvé(s)")
            # Analyser les 5 premiers PDF max
            for i, pdf in enumerate(pdf_urls[:5], 1):
                texte = extraire_texte_pdf(pdf["url"])
                if texte:
                    contenu_pdf += " " + texte
                    pdf_analyses.append({
                        "url": pdf["url"],
                        "texte": pdf["texte"],
                        "contenu_extrait": True,
                        "longueur": len(texte)
                    })
                else:
                    pdf_analyses.append({
                        "url": pdf["url"],
                        "texte": pdf["texte"],
                        "contenu_extrait": False
                    })
        
        # Texte complet
        texte_complet = f"{titre} {contenu} {contenu_pdf} {description}"
        
        # 💻 ÉTAPE 2 : Vérifier si c'est informatique
        print(f"         💻 Analyse informatique...")
        est_info, score_info = est_informatique(texte_complet)
        
        if est_info:
            print(f"         🎯 INFORMATIQUE ! (score: {score_info:.2%})")
            
            # 🆕 Si informatique, garder seulement les 5 PDF les plus pertinents
            if len(pdf_urls) > 5:
                # Prioriser les PDF avec contenu extrait et pertinent
                pdf_urls_pertinents = [p for p in pdf_analyses if p.get("contenu_extrait")]
                if len(pdf_urls_pertinents) > 5:
                    pdf_urls_pertinents = pdf_urls_pertinents[:5]
                pdf_urls = pdf_urls_pertinents
                print(f"         📄 {len(pdf_urls)} PDF sélectionnés (informatique)")
        
        return {
            "titre": titre,
            "contenu": texte_complet[:2000],
            "contenu_pdf": contenu_pdf[:1000],
            "description": description,
            "longueur_contenu": len(texte_complet),
            "liens_pdf": pdf_urls if not est_info else pdf_urls[:5],  # Max 5 pour informatique
            "nb_pdf": len(pdf_urls),
            "nb_pdf_analyses": len([p for p in pdf_analyses if p.get("contenu_extrait")]),
            "est_appel_offres": est_ao,
            "appel_offres_score": score_ao,
            "appel_offres_methode": methode,
            "est_informatique_ia": est_info,
            "ia_score": score_info,
            "ia_model": "local" if USE_LOCAL_MODEL else "bert",
            "source_entite": source_info.get("nom_entite", ""),
            "source_categorie": source_info.get("categorie", "")
        }
        
    except Exception as e:
        print(f"         ❌ Erreur : {str(e)[:50]}")
        return None


def main():
    """Scraper intelligent avec double filtrage"""
    print("\n" + "="*70)
    print("🧠 SCRAPER INTELLIGENT - Double Filtrage IA")
    print("="*70)
    
    sources = list(sources_collection.find({}))
    
    if not sources:
        print("\n❌ Aucune source trouvée")
        return
    
    print(f"\n📊 {len(sources)} source(s) trouvée(s)\n")
    
    total_liens_trouves = 0
    total_filtres_ao = 0
    total_appels_offres = 0
    total_nouveaux = 0
    total_informatique = 0
    
    for idx_source, source in enumerate(sources, 1):
        source_url = source.get("url", "")
        source_nom = source.get("nom_entite", "Sans nom")
        
        print(f"\n{'='*70}")
        print(f"[{idx_source}/{len(sources)}] 🔍 {source_nom}")
        print(f"{'='*70}")
        print(f"   🌐 {source_url}")
        
        # Extraire liens
        print(f"\n      📡 Extraction des liens...")
        liens_trouves = extraire_liens_de_source(source_url)
        total_liens_trouves += len(liens_trouves)
        print(f"      ✅ {len(liens_trouves)} lien(s) trouvé(s)")
        
        # 🆕 LIMITER à 100 DERNIERS LIENS (les plus récents)
        if len(liens_trouves) > 100:
            # Inverser pour avoir les derniers en premier (généralement les plus récents)
            liens_trouves = liens_trouves[-100:]
            print(f"      ⚠️ Limitation à 100 derniers liens (source trop grande)")
        
        # Analyser chaque lien
        for idx_lien, lien_url in enumerate(liens_trouves, 1):
            print(f"\n      [{idx_lien}/{len(liens_trouves)}] ──────────────")
            print(f"      🔗 {lien_url[:55]}...")
            
            # 🗑️ NOUVEAU : Vérifier si existe OU en corbeille
            lien_existant = liens_collection.find_one({"url": lien_url})
            if lien_existant:
                # Si en corbeille, ignorer complètement (pas de réanalyse)
                if lien_existant.get("en_corbeille") or lien_existant.get("ignore_rescrape"):
                    print(f"         🗑️  En corbeille - Ignoré")
                    continue
                print(f"         ⏭️  Déjà dans la base")
                continue
            
            # Analyser avec filtrage intelligent
            data = analyser_lien_intelligent(lien_url, source)
            
            if not data:
                total_filtres_ao += 1
                continue
            
            total_appels_offres += 1
            
            # Ajouter dans la base
            lien_doc = {
                "url": lien_url,
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
                "nb_pdf_analyses": data.get("nb_pdf_analyses", 0),
                "est_appel_offres": data["est_appel_offres"],
                "appel_offres_score": data["appel_offres_score"],
                "est_informatique_ia": data["est_informatique_ia"],
                "ia_score": data["ia_score"],
                "ia_model": MODEL_TYPE,
                "is_processed_by_model": True,
                "analysis_result": {
                    "est_informatique_ia": data["est_informatique_ia"],
                    "score": data["ia_score"],
                    "model": MODEL_TYPE,
                    "date_analyse": datetime.now()
                }
            }
            
            liens_collection.insert_one(lien_doc)
            total_nouveaux += 1
            
            if data["est_informatique_ia"]:
                total_informatique += 1
            
            print(f"         ✅ Ajouté")
    
    # Résumé
    print(f"\n{'='*70}")
    print(f"✅ SCRAPING INTELLIGENT TERMINÉ")
    print(f"{'='*70}")
    print(f"📊 Statistiques :")
    print(f"   - Liens trouvés : {total_liens_trouves}")
    print(f"   - ⏭️  Filtrés (pas AO) : {total_filtres_ao}")
    print(f"   - ✅ Appels d'offres : {total_appels_offres}")
    print(f"   - 🆕 Nouveaux ajoutés : {total_nouveaux}")
    print(f"   - 💻 Informatique : {total_informatique}")
    print(f"\n💡 Efficacité du filtre : {(total_filtres_ao/total_liens_trouves*100):.1f}% de liens inutiles évités !" if total_liens_trouves > 0 else "")


if __name__ == "__main__":
    main()

