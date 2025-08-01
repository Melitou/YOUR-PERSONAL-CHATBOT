// Simple API client for authentication
class ApiClient {
    private baseURL: string;

    constructor(baseURL: string = 'http://localhost:8000') {
        this.baseURL = baseURL;
    }

    private getAuthHeaders(): HeadersInit {
        const token = localStorage.getItem('authToken');
        return {
            'Content-Type': 'application/json',
            ...(token && { 'Authorization': `Bearer ${token}` })
        };
    }

    private async handleResponse(response: Response) {
        if (response.status === 401) {
            // Token expired or invalid
            localStorage.removeItem('authToken');
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Unknown error' }));
            throw new Error(error.message || 'Request failed');
        }

        return response.json();
    }

    async post(endpoint: string, data: any) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(data),
        });
        return this.handleResponse(response);
    }

    async get(endpoint: string) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'GET',
            headers: this.getAuthHeaders(),
        });
        return this.handleResponse(response);
    }
}

export const apiClient = new ApiClient();

// Authentication API
export const authApi = {
    login: (credentials: { username: string; password: string }) =>
        apiClient.post('/login', credentials),
    
    logout: () =>
        apiClient.post('/logout', {}),
    
    getCurrentUser: () =>
        apiClient.get('/me'),
};