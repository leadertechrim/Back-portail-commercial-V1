"""
Scraper INTELLIGENT avec OpenRouter AI :
- Détection appels d'offres par mots-clés
- Classification informatique par OpenRouter (100% précision)
- Enregistrement dans appels_doffres_liens_new
"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from database import db, sources_col
import re
import io
import os

try:
    import PyPDF2
except:
    print("⚠️ PyPDF2 non installé")
    PyPDF2 = None

# MongoDB - Utiliser les collections depuis database.py
sources_collection = sources_col  # sources_col pointe déjà vers appels_doffres_sourcess
liens_collection = db["appels_doffres_liens_new"]

# Configuration OpenRouter
USE_OPENROUTER = os.getenv('USE_OPENROUTER', 'true').lower() == 'true'

print("="*70)
print("🧠 SCRAPER AVEC OPENROUTER AI")
print("="*70)
print(f"🤖 OpenRouter activé: {USE_OPENROUTER}")

if USE_OPENROUTER:
    try:
        from classifier_openrouter_optimized import analyser_avec_openrouter
        print("✅ OpenRouter chargé avec succès")
    except Exception as e:
        print(f"⚠️ Erreur chargement OpenRouter: {e}")
        USE_OPENROUTER = False


def est_appel_offres(texte, url):
    """
    FILTRE 1 : Vérifie si c'est vraiment un appel d'offres
    """
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
        
        # Mots-clés appels d'offres
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


def est_informatique(texte, titre=""):
    """
    FILTRE 2 : Vérifie si c'est informatique avec OpenRouter
    """
    try:
        if not texte or len(texte.strip()) < 50:
            return False, 0.0
        
        if USE_OPENROUTER:
            # Utiliser OpenRouter
            est_info, score = analyser_avec_openrouter(texte, titre)
            if est_info is not None:
                return est_info, score
        
        # Fallback : mots-clés si OpenRouter indisponible
        mots_cles_info = [
            "informatique", "logiciel", "software", "développement", "système d'information",
            "base de données", "réseau", "serveur", "cloud", "cybersécurité",
            "application", "web", "mobile", "api", "erp", "crm"
        ]
        
        texte_lower = texte.lower()
        nb_matches = sum(1 for mot in mots_cles_info if mot in texte_lower)
        
        if nb_matches >= 2:
            score = min(0.6 + (nb_matches * 0.1), 0.95)
            return True, score
        
        return False, 0.0
        
    except Exception as e:
        print(f"            ⚠️ Erreur classification IT : {str(e)[:40]}")
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
    """Extrait PDF (limité à 10)"""
    pdf_urls = []
    
    for a in soup.find_all("a", href=True):
        if a["href"].lower().endswith('.pdf'):
            pdf_urls.append({
                "url": normaliser_url(a["href"], page_url),
                "texte": a.get_text().strip() or "PDF"
            })
    
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
    Analyse intelligente en 2 étapes avec OpenRouter
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
        
        # Texte préliminaire
        texte_preliminaire = f"{titre} {contenu[:500]} {description}"
        
        # 🔍 ÉTAPE 1 : Vérifier si c'est un appel d'offres
        print(f"         🔍 Filtre appel d'offres...")
        est_ao, score_ao, methode = est_appel_offres(texte_preliminaire, url)
        
        if not est_ao:
            print(f"         ⏭️  Pas un appel d'offres ({methode})")
            return None
        
        print(f"         ✅ Appel d'offres confirmé")
        
        # PDF
        pdf_urls = extraire_pdf_urls(soup, url)
        contenu_pdf = ""
        
        if pdf_urls:
            print(f"         📄 {len(pdf_urls)} PDF trouvé(s)")
            for pdf in pdf_urls[:3]:  # Max 3 PDF
                texte = extraire_texte_pdf(pdf["url"])
                if texte:
                    contenu_pdf += " " + texte
        
        # Texte complet
        texte_complet = f"{titre} {contenu} {contenu_pdf} {description}"
        
        # 💻 ÉTAPE 2 : Vérifier si c'est informatique (OpenRouter)
        print(f"         🤖 Analyse OpenRouter...")
        est_info, score_info = est_informatique(texte_complet, titre)
        
        if est_info:
            print(f"         🎯 INFORMATIQUE ! (score: {score_info:.2%})")
        else:
            print(f"         ⏭️  Non informatique (score: {score_info:.2%})")
        
        return {
            "titre": titre,
            "contenu": texte_complet[:2000],
            "contenu_pdf": contenu_pdf[:1000],
            "description": description,
            "longueur_contenu": len(texte_complet),
            "liens_pdf": pdf_urls[:5],
            "nb_pdf": len(pdf_urls),
            "est_appel_offres": est_ao,
            "appel_offres_score": score_ao,
            "appel_offres_methode": methode,
            "est_informatique_ia": est_info,
            "ia_score": score_info,
            "ia_model": "openrouter" if USE_OPENROUTER else "keywords",
            "source_entite": source_info.get("nom_entite", ""),
            "source_categorie": source_info.get("categorie", "")
        }
        
    except Exception as e:
        print(f"         ❌ Erreur : {str(e)[:50]}")
        return None


def main():
    """Scraper intelligent avec OpenRouter"""
    print("\n" + "="*70)
    print("🧠 SCRAPER AVEC OPENROUTER")
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
        
        # Limiter à 100 derniers liens
        if len(liens_trouves) > 100:
            liens_trouves = liens_trouves[-100:]
            print(f"      ⚠️ Limitation à 100 derniers liens")
        
        # Analyser chaque lien
        for idx_lien, lien_url in enumerate(liens_trouves, 1):
            print(f"\n      [{idx_lien}/{len(liens_trouves)}] ──────────────")
            print(f"      🔗 {lien_url[:55]}...")
            
            # Vérifier si existe
            lien_existant = liens_collection.find_one({"url": lien_url})
            if lien_existant:
                if lien_existant.get("en_corbeille") or lien_existant.get("ignore_rescrape"):
                    print(f"         🗑️  En corbeille - Ignoré")
                    continue
                print(f"         ⏭️  Déjà dans la base")
                continue
            
            # Analyser
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
                },
                "en_corbeille": False,
                "masque": False
            }
            
            liens_collection.insert_one(lien_doc)
            total_nouveaux += 1
            
            if data["est_informatique_ia"]:
                total_informatique += 1
            
            print(f"         ✅ Ajouté")
    
    # Résumé
    print(f"\n{'='*70}")
    print(f"✅ SCRAPING TERMINÉ")
    print(f"{'='*70}")
    print(f"📊 Statistiques :")
    print(f"   - Liens trouvés : {total_liens_trouves}")
    print(f"   - ⏭️  Filtrés (pas AO) : {total_filtres_ao}")
    print(f"   - ✅ Appels d'offres : {total_appels_offres}")
    print(f"   - 🆕 Nouveaux ajoutés : {total_nouveaux}")
    print(f"   - 💻 Informatique : {total_informatique}")


if __name__ == "__main__":
    main()

