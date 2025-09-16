// Gestion de l'authentification
class AuthManager {
    constructor() {
        this.token = localStorage.getItem('authToken');
        this.user = JSON.parse(localStorage.getItem('user') || '{}');
    }

    // Connexion
    async login(email, password) {
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Erreur de connexion');
            }

            const data = await response.json();
            this.token = data.token;
            this.user = { 
                name: data.name, 
                role: data.role, 
                email: email 
            };

            // Sauvegarder dans le localStorage
            localStorage.setItem('authToken', this.token);
            localStorage.setItem('user', JSON.stringify(this.user));

            return data;
        } catch (error) {
            console.error('Erreur de connexion:', error);
            throw error;
        }
    }

    // Déconnexion
    logout() {
        this.token = null;
        this.user = {};
        localStorage.removeItem('authToken');
        localStorage.removeItem('user');
    }

    // Vérifier si l'utilisateur est connecté
    isLoggedIn() {
        return !!this.token;
    }

    // Vérifier si l'utilisateur est admin
    isAdmin() {
        return this.user.role === 'admin';
    }

    // Obtenir les headers d'authentification
    getAuthHeaders() {
        return {
            'Authorization': `Bearer ${this.token}`,
            'Content-Type': 'application/json'
        };
    }

    // Requête authentifiée
    async authenticatedFetch(url, options = {}) {
        if (!this.isLoggedIn()) {
            throw new Error('Utilisateur non connecté');
        }

        const authOptions = {
            ...options,
            headers: {
                ...this.getAuthHeaders(),
                ...options.headers
            }
        };

        const response = await fetch(url, authOptions);
        
        if (response.status === 401) {
            this.logout();
            throw new Error('Session expirée');
        }

        return response;
    }
}

// Instance globale
const auth = new AuthManager();

// Fonctions utilitaires pour l'API
async function fetchUsers() {
    try {
        const response = await auth.authenticatedFetch('/api/users');
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Erreur lors du chargement des utilisateurs:', error);
        throw error;
    }
}

async function fetchUserStats() {
    try {
        const response = await auth.authenticatedFetch('/api/users/stats');
        if (!response.ok) {
            throw new Error(`Erreur ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error('Erreur lors du chargement des statistiques:', error);
        throw error;
    }
}

// Export pour utilisation dans d'autres scripts
window.auth = auth;
window.fetchUsers = fetchUsers;
window.fetchUserStats = fetchUserStats;
