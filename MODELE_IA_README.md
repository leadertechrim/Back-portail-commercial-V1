# 🤖 Système de Détection IA pour les Appels d'Offres Informatiques

## 📋 Vue d'ensemble

Ce projet utilise un système intelligent à **double filtrage** pour identifier automatiquement les appels d'offres informatiques :

1. **Filtre 1** : Détection des appels d'offres (vs pages informatives)
2. **Filtre 2** : Classification informatique (vs autres domaines)

## 🎯 Types de Modèles Supportés

Le système supporte **3 types de modèles** avec fallback automatique :

### 1. 🏠 Modèle Local (Recommandé si disponible)
- **Dossier** : `model_appel_offre_ai/`
- **Avantage** : Modèle entraîné spécifiquement pour vos besoins
- **Format** : Compatible HuggingFace Transformers
- **Utilisation** : Chargé automatiquement s'il existe

### 2. 🌐 Modèle Open Source Zero-Shot (Utilisé actuellement)
- **Modèle** : `facebook/bart-large-mnli`
- **Avantage** : Ne nécessite aucun entraînement
- **Performance** : Très bon pour la classification générique
- **Labels utilisés** :
  - "informatique et technologies"
  - "travaux et construction"
  - "fournitures de bureau"
  - "services généraux"

### 3. 🔤 Mots-clés (Fallback ultime)
- **Utilisation** : Si les modèles IA ne sont pas disponibles
- **Mots-clés surveillés** :
  - informatique, logiciel, software
  - réseau, serveur, base de données
  - système d'information, SI, cloud
  - cybersécurité, ERP, CRM
  - infrastructure IT, data center
  - et bien d'autres...

## 🚀 Comment ça fonctionne ?

### Flux de détection

```
📄 Document → 🔍 Filtre Appel d'Offres → 💻 Filtre Informatique → ✅ Résultat
```

### Exemple concret

```python
# 1. Texte analysé
texte = "Appel d'offres pour acquisition de serveurs et logiciels ERP"

# 2. Filtre 1 : C'est un appel d'offres ?
✅ OUI (score: 0.85)

# 3. Filtre 2 : C'est de l'informatique ?
# - Zero-shot : "informatique et technologies" → score: 0.78
# - Mots-clés trouvés : serveurs, logiciels, ERP (3 mots-clés)
✅ OUI (score final: 0.78)

# 4. Résultat → Ajouté à la base de données
```

## 📦 Installation d'un Modèle Local (Optionnel)

Si vous avez entraîné un modèle spécifique, suivez ces étapes :

### Option 1 : Modèle HuggingFace existant

```bash
# Télécharger un modèle depuis HuggingFace
python -c "
from transformers import AutoTokenizer, AutoModelForSequenceClassification

model_name = 'votre-modele-huggingface'  # Ex: 'camembert-base'
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# Sauvegarder localement
tokenizer.save_pretrained('model_appel_offre_ai')
model.save_pretrained('model_appel_offre_ai')
"
```

### Option 2 : Modèle personnalisé entraîné

```bash
# Créer le dossier
mkdir model_appel_offre_ai

# Copier vos fichiers de modèle
cp votre_modele/* model_appel_offre_ai/
```

### Structure attendue

```
model_appel_offre_ai/
├── config.json
├── pytorch_model.bin (ou model.safetensors)
├── tokenizer_config.json
├── vocab.txt (ou tokenizer.json)
└── special_tokens_map.json
```

### Format de sortie attendu

Votre modèle doit produire des labels dans ce format :
- `"LABEL_1"` ou `"informatique"` ou `"IT"` ou `"1"` → Informatique
- `"LABEL_0"` ou autre → Pas informatique

## 📊 Scores et Seuils

### Modèle Zero-Shot
- **Seuil de confiance** : 0.4 (avec vérification mots-clés)
- **Seuil élevé** : 0.6 (accepté sans vérification)
- **Fallback mots-clés** : 3+ mots-clés → Accepté (score 0.75)

### Modèle Local
- **Seuil de confiance** : 0.6
- **Labels acceptés** : LABEL_1, informatique, IT, 1

### Mots-clés seuls
- **Minimum** : 2 mots-clés différents
- **Score** : 0.7 + (nombre de mots-clés × 0.05), max 0.95

## 🔧 Configuration

### Fichiers concernés

Les 3 scrapers utilisent le même système :
- `scraper_smart_filter.py` - Scraping intelligent avec double filtrage
- `scraper_instant_display.py` - Affichage instantané avec analyse en arrière-plan
- `scraper_parallel_optimized.py` - Scraping parallèle ultra-rapide

### Variables de configuration

```python
# Dans chaque scraper
MODEL_TYPE = "local" | "zero-shot" | "keywords"
USE_LOCAL_MODEL = True | False
USE_FILTRE = True | False
```

## 📈 Performance

### Modèle Zero-Shot (Actuel)

✅ **Avantages** :
- Pas besoin d'entraînement
- Fonctionne immédiatement
- Très précis pour la classification générique
- Combine IA + mots-clés pour plus de précision

⚠️ **Limitations** :
- Légèrement plus lent qu'un modèle local
- Nécessite une connexion pour le premier téléchargement

### Avec Modèle Local (Si disponible)

✅ **Avantages** :
- Plus rapide (pas de téléchargement)
- Peut être entraîné sur vos données spécifiques
- Meilleure précision pour vos cas d'usage

⚠️ **Limitations** :
- Nécessite un entraînement préalable
- Prend de l'espace disque

## 🛠️ Dépannage

### Problème : "Modèle non trouvé"

```
⚠️ Modèle local non disponible : [Errno 2] No such file or directory: 'model_appel_offre_ai'
📦 Chargement du modèle open source (Zero-Shot)...
✅ Modèle open source chargé
```

**Solution** : C'est normal ! Le système utilise automatiquement le modèle zero-shot open source.

### Problème : "Out of memory"

**Solution** : Le modèle zero-shot peut être gourmand en mémoire. Options :
1. Utiliser un modèle plus léger
2. Augmenter la RAM disponible
3. Utiliser uniquement les mots-clés (MODEL_TYPE = "keywords")

### Problème : Trop de faux positifs

**Solutions** :
1. Augmenter les seuils de confiance dans le code
2. Ajouter plus de mots-clés spécifiques
3. Entraîner un modèle local sur vos données

### Problème : Trop de faux négatifs

**Solutions** :
1. Diminuer les seuils de confiance
2. Ajouter des synonymes dans les mots-clés
3. Vérifier que les textes analysés sont suffisamment longs (min 50 caractères)

## 📚 Ressources

### Modèles HuggingFace recommandés

Pour le français :
- `camembert-base` - Modèle français général
- `flaubert/flaubert_base_cased` - Bon pour le français
- `almanach/camembert-base` - Classification française

Multilingues :
- `xlm-roberta-base` - Excellent pour plusieurs langues
- `bert-base-multilingual-cased` - Classique multilingue

### Documentation Transformers

- [HuggingFace Transformers](https://huggingface.co/docs/transformers)
- [Zero-Shot Classification](https://huggingface.co/tasks/zero-shot-classification)
- [Fine-tuning Guide](https://huggingface.co/docs/transformers/training)

## 🎓 Entraîner votre propre modèle

Si vous souhaitez créer un modèle personnalisé :

1. **Collecter des données** : 
   - Minimum 500-1000 exemples d'appels d'offres
   - 50% informatiques, 50% non-informatiques

2. **Préparer le dataset** :
   ```python
   # Format CSV
   texte,label
   "Appel d'offres serveurs...",1
   "Appel d'offres travaux...",0
   ```

3. **Entraîner** :
   ```python
   from transformers import AutoModelForSequenceClassification, Trainer
   # ... code d'entraînement
   ```

4. **Sauvegarder** :
   ```python
   model.save_pretrained('model_appel_offre_ai')
   tokenizer.save_pretrained('model_appel_offre_ai')
   ```

## 💡 Bonnes Pratiques

1. **Commencer avec le modèle zero-shot** (actuel) - Aucune configuration requise
2. **Monitorer les résultats** - Vérifier la précision sur quelques semaines
3. **Ajuster les seuils** si nécessaire selon vos besoins
4. **Entraîner un modèle local** seulement si vous avez beaucoup de données

## 🆘 Support

Pour toute question ou problème :
1. Vérifier les logs de console lors du démarrage du scraper
2. Consulter la variable `MODEL_TYPE` dans les résultats de la base de données
3. Tester avec des exemples connus (vrais appels d'offres informatiques)

---

**Version actuelle** : Système utilisant le modèle zero-shot `facebook/bart-large-mnli` ✅
**Statut** : Opérationnel et prêt à l'emploi ! 🚀


