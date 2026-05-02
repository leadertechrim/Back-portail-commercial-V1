# -*- coding: utf-8 -*-
"""Classification optimisée avec OpenRouter"""
import requests
import os

OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'anthropic/claude-3-haiku')

def analyser_avec_openrouter(texte, titre=""):
    """
    Analyse avec OpenRouter - Version optimisée
    Retourne (est_info, score) ou (None, 0) si erreur
    """
    
    # Limiter le texte pour économiser tokens
    texte_limite = texte[:800]
    
    prompt = f"""Analysez cet appel d'offres et determinez s'il concerne l'informatique/IT.

Titre: {titre}

Contenu: {texte_limite}

Repondez UNIQUEMENT par "OUI" ou "NON" suivi d'un score (0-100).
Format exact: OUI 95 ou NON 80

Informatique = logiciels, developpement web/mobile, serveurs, cloud, reseaux, cybersecurite, ERP, CRM, materiel IT, sites web, bases de donnees, infrastructure IT.

NON informatique = mobilier, construction, nettoyage, vehicules, formation non-IT."""

    try:
        response = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://appeloffreIA.com",
                "X-Title": "AppelOffreIA"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 10,
                "temperature": 0
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip().upper()
            
            # Parser la reponse "OUI 95" ou "NON 80"
            parts = content.split()
            if len(parts) >= 1:
                reponse = parts[0]
                score = int(parts[1]) / 100 if len(parts) > 1 else 0.5
                
                # Seuil minimum de 60% pour éviter les faux positifs
                est_info = reponse in ["OUI", "YES", "Y", "TRUE"] and score >= 0.60
                
                return est_info, score
            else:
                return None, 0
        else:
            print(f"         Erreur OpenRouter API: {response.status_code}")
            return None, 0
            
    except requests.exceptions.Timeout:
        print(f"         Timeout OpenRouter")
        return None, 0
    except Exception as e:
        print(f"         Erreur OpenRouter: {str(e)[:50]}")
        return None, 0

