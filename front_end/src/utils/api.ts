// Secure API helper with automatic token management
class ApiClient {
    private baseURL: string;

    constructor(baseURL: string = '/api') {
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
            window.location.href = '/login';
            throw new Error('Authentication required');
        }

        if (response.status === 403) {
            throw new Error('Insufficient permissions');
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Unknown error' }));
            throw new Error(error.message || 'Request failed');
        }

        return response.json();
    }

    async get(endpoint: string) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'GET',
            headers: this.getAuthHeaders(),
        });
        return this.handleResponse(response);
    }

    async post(endpoint: string, data: any) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(data),
        });
        return this.handleResponse(response);
    }

    async put(endpoint: string, data: any) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'PUT',
            headers: this.getAuthHeaders(),
            body: JSON.stringify(data),
        });
        return this.handleResponse(response);
    }

    async delete(endpoint: string) {
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'DELETE',
            headers: this.getAuthHeaders(),
        });
        return this.handleResponse(response);
    }

    // Special method for file uploads
    async uploadFiles(endpoint: string, formData: FormData) {
        const token = localStorage.getItem('authToken');
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            method: 'POST',
            headers: {
                ...(token && { 'Authorization': `Bearer ${token}` })
                // Don't set Content-Type for FormData - browser will set it with boundary
            },
            body: formData,
        });
        return this.handleResponse(response);
    }
}

export const apiClient = new ApiClient();

// Specific API functions with proper typing
export const authApi = {
    login: (credentials: { email: string; password: string }) =>
        apiClient.post('/auth/login', credentials),
    
    logout: () =>
        apiClient.post('/auth/logout', {}),
    
    getCurrentUser: () =>
        apiClient.get('/auth/me'),
    
    refreshToken: () =>
        apiClient.post('/auth/refresh', {}),
};

export const agentApi = {
    // Regular user agent creation
    createUserAgent: (data: {
        name: string;
        description: string;
        aiProvider: string;
        files: File[];
    }) => {
        const formData = new FormData();
        formData.append('name', data.name);
        formData.append('description', data.description);
        formData.append('aiProvider', data.aiProvider);
        
        data.files.forEach((file) => {
            formData.append(`files`, file);
        });

        return apiClient.uploadFiles('/agents/user', formData);
    },

    // SuperUser agent creation - backend will verify permissions
    createSuperUserAgent: (data: {
        name: string;
        description: string;
        files: File[];
        chunkingMethod: string;
        embeddingModel: string;
    }) => {
        const formData = new FormData();
        formData.append('name', data.name);
        formData.append('description', data.description);
        formData.append('chunkingMethod', data.chunkingMethod);
        formData.append('embeddingModel', data.embeddingModel);
        
        data.files.forEach((file) => {
            formData.append(`files`, file);
        });

        return apiClient.uploadFiles('/agents/superuser', formData);
    },

    // Get available options (only if user has permission)
    getEmbeddingModels: () =>
        apiClient.get('/agents/embedding-models'),
    
    getChunkingMethods: () =>
        apiClient.get('/agents/chunking-methods'),
    
    // Chatbot management endpoints
    getUserAgents: () =>
        apiClient.get('/agents/user/list'),
    
    deleteAgent: (agentId: string) =>
        apiClient.delete(`/agents/${agentId}`),
    
    updateAgent: (agentId: string, data: {
        name?: string;
        description?: string;
        isActive?: boolean;
    }) =>
        apiClient.put(`/agents/${agentId}`, data),
    
    getAgentById: (agentId: string) =>
        apiClient.get(`/agents/${agentId}`),
};

export const chatApi = {
    sendMessage: (data: { message: string; agentId?: string }) =>
        apiClient.post('/chat/message', data),
    
    getChatHistory: (agentId?: string) =>
        apiClient.get(`/chat/history${agentId ? `?agentId=${agentId}` : ''}`),
    
    clearChatHistory: (agentId?: string) =>
        apiClient.delete(`/chat/history${agentId ? `?agentId=${agentId}` : ''}`),
};