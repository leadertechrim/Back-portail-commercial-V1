# API Routes pour les Nouvelles Collections

## Collections Disponibles

### 1. CLIENTS

Collection pour gérer les clients de l'entreprise.

### 2. PARTENAIRES

Collection pour gérer les partenaires de l'entreprise.

### 3. PERSONNELS

Collection pour gérer le personnel de l'entreprise.

## Routes API

### CLIENTS

#### Récupérer tous les clients

**GET** `/api/clients`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Liste de tous les clients

#### Créer un nouveau client

**POST** `/api/clients`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:**

```json
{
  "raison_sociale": "Ministère de la Transformation numérique",
  "nom_prenom": "Ahmed Ould Mohamed",
  "telephone": "+22245213456",
  "whatsapp": "+22245213456",
  "email": "contact@numerique.gov.mr",
  "adresse": "Avenue Gamal Abdel Nasser, Nouakchott",
  "note_commentaire": "Client stratégique du secteur public, relation à long terme."
}
```

#### Récupérer un client spécifique

**GET** `/api/clients/<client_id>`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Détails du client

#### Modifier un client

**PUT** `/api/clients/<client_id>`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:** Mêmes champs que la création

#### Supprimer un client

**DELETE** `/api/clients/<client_id>`

- **Headers:** `Authorization: Bearer <token>` (admin requis)

### PARTENAIRES

#### Récupérer tous les partenaires

**GET** `/api/partenaires`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Liste de tous les partenaires

#### Créer un nouveau partenaire

**POST** `/api/partenaires`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:**

```json
{
  "raison_sociale": "TechAfrica Solutions",
  "nom_prenom": "Fatou Diop",
  "telephone": "+221776543210",
  "whatsapp": "+221776543210",
  "email": "fatou.diop@techafrica.com",
  "adresse": "Immeuble Africa Tower, Dakar",
  "note_commentaire": "Partenaire fiable pour les projets digitaux transfrontaliers."
}
```

#### Récupérer un partenaire spécifique

**GET** `/api/partenaires/<partenaire_id>`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Détails du partenaire

#### Modifier un partenaire

**PUT** `/api/partenaires/<partenaire_id>`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:** Mêmes champs que la création

#### Supprimer un partenaire

**DELETE** `/api/partenaires/<partenaire_id>`

- **Headers:** `Authorization: Bearer <token>` (admin requis)

### PERSONNELS

#### Récupérer tous les personnels

**GET** `/api/personnels`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Liste de tous les personnels

#### Créer un nouveau personnel

**POST** `/api/personnels`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:**

```json
{
  "nom_prenom": "Mohamed Salem",
  "telephone": "+22236457890",
  "whatsapp": "+22236457890",
  "email": "m.salem@entreprise.mr",
  "adresse": "Tevragh Zeina, Nouakchott",
  "note_commentaire": "Très professionnel, ponctuel et compétent."
}
```

#### Récupérer un personnel spécifique

**GET** `/api/personnels/<personnel_id>`

- **Headers:** `Authorization: Bearer <token>` (optionnel)
- **Réponse:** Détails du personnel

#### Modifier un personnel

**PUT** `/api/personnels/<personnel_id>`

- **Headers:**
  - `Authorization: Bearer <token>` (admin requis)
  - `Content-Type: application/json`
- **Body:** Mêmes champs que la création

#### Supprimer un personnel

**DELETE** `/api/personnels/<personnel_id>`

- **Headers:** `Authorization: Bearer <token>` (admin requis)

## Champs Communs

### Champs requis

- **Clients & Partenaires:**

  - `raison_sociale` (string, requis)
  - `nom_prenom` (string, requis)
  - `telephone` (string, requis, format international)
  - `email` (string, requis, format email valide)

- **Personnels:**
  - `nom_prenom` (string, requis)
  - `telephone` (string, requis, format international)
  - `email` (string, requis, format email valide)

### Champs optionnels

- `whatsapp` (string, format international)
- `adresse` (string)
- `note_commentaire` (string)

### Champs automatiques

- `_id` (ObjectId, généré automatiquement)
- `created_at` (datetime, généré automatiquement)
- `updated_at` (datetime, mis à jour automatiquement)

## Exemples d'utilisation avec JavaScript

### Récupérer tous les clients

```javascript
const fetchClients = async (token) => {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/clients", {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Erreur lors de la récupération des clients:", error);
    throw error;
  }
};
```

### Créer un nouveau client

```javascript
const createClient = async (clientData, token) => {
  try {
    const response = await fetch("http://127.0.0.1:8000/api/clients", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(clientData),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.message || `HTTP error! status: ${response.status}`
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Erreur lors de la création du client:", error);
    throw error;
  }
};
```

### Modifier un client

```javascript
const updateClient = async (clientId, clientData, token) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/clients/${clientId}`,
      {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(clientData),
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.message || `HTTP error! status: ${response.status}`
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Erreur lors de la modification du client:", error);
    throw error;
  }
};
```

### Supprimer un client

```javascript
const deleteClient = async (clientId, token) => {
  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/clients/${clientId}`,
      {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        errorData.message || `HTTP error! status: ${response.status}`
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Erreur lors de la suppression du client:", error);
    throw error;
  }
};
```

## Codes de Statut HTTP

- `200`: Succès
- `201`: Créé avec succès
- `400`: Erreur de validation
- `401`: Non autorisé
- `403`: Accès refusé (admin requis)
- `404`: Non trouvé
- `500`: Erreur serveur

## Validation des Champs

- **Email:** Format email valide
- **Téléphone/WhatsApp:** Format international (+22212345678)
- **Raison sociale:** Non vide, minimum 1 caractère
- **Nom/Prénom:** Non vide, minimum 1 caractère
- **Adresse:** String valide
- **Note/Commentaire:** String valide
