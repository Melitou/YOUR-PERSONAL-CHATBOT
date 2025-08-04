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


// Chatbot API
export const chatbotApi = {
    createSuperUserChatbot: async (
        name: string,
        description: string,
        files: File[],  
        chunkingMethod: string,
        embeddingModel: string
    ) => {
        const formData = new FormData();
        formData.append('agent_provider', '');
        formData.append('agent_description', description);
        formData.append('chunking_method', fix_chunking_method(chunkingMethod));
        formData.append('embedding_model', embeddingModel);
        formData.append('user_namespace', name);
        
        files.forEach((file) => {
            formData.append('files', file);
        });

        const token = localStorage.getItem('authToken');
        const response = await fetch(`${apiClient['baseURL']}/create_agent`, {
            method: 'POST',
            headers: {
                ...(token && { 'Authorization': `Bearer ${token}` }),
            },
            body: formData,
        });

        if (response.status === 401) {
            localStorage.removeItem('authToken');
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.text();
                console.error('Server response:', errorData);
                
                try {
                    const errorJson = JSON.parse(errorData);
                    errorMessage = errorJson.message || errorJson.detail || errorMessage;
                } catch {
                    errorMessage = errorData || errorMessage;
                }
            } catch (parseError) {
                console.error('Failed to parse error response:', parseError);
            }
            
            throw new Error(`Failed to create chatbot: ${errorMessage}`);
        }

        return response.json();
    },

    createNormalUserChatbot: async (
        name: string,
        description: string,
        files: File[],  
        agent_provider: string,
    ) => {
        const formData = new FormData();
        formData.append('agent_provider', agent_provider);
        formData.append('agent_description', description);
        formData.append('chunking_method', '');
        formData.append('embedding_model', '');
        formData.append('user_namespace', name);

        files.forEach((file) => {
            formData.append('files', file);
        });

        const token = localStorage.getItem('authToken');
        const response = await fetch(`${apiClient['baseURL']}/create_agent`, {
            method: 'POST',
            headers: {
                ...(token && { 'Authorization': `Bearer ${token}` }),
            },
            body: formData,
        });

        if (response.status === 401) {
            localStorage.removeItem('authToken');
            throw new Error('Authentication required');
        }

        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            try {
                const errorData = await response.text();
                console.error('Server response:', errorData);
                
                try {
                    const errorJson = JSON.parse(errorData);
                    errorMessage = errorJson.message || errorJson.detail || errorMessage;
                } catch {
                    errorMessage = errorData || errorMessage;
                }
            } catch (parseError) {
                console.error('Failed to parse error response:', parseError);
            }
            
            throw new Error(`Failed to create chatbot: ${errorMessage}`);
        }

        return response.json();
    },

    // Get all chatbots for the current user
    getUserChatbots: () =>
        apiClient.get('/chatbots'),

    // Delete a chatbot
    deleteChatbot: (chatbotId: string) =>
        apiClient.post(`/chatbots/${chatbotId}/delete`, {}),

    // Get chatbot details
    getChatbotDetails: (chatbotId: string) =>
        apiClient.get(`/chatbots/${chatbotId}`),
};

// ['token', 'semantic', 'line', 'recursive']
function fix_chunking_method(chunkingMethod: string): string {
    if (chunkingMethod === 'Fixed Token') {
        return 'token';
    }
    if (chunkingMethod === 'Semantic') {
        return 'semantic';
    }
    if (chunkingMethod === 'Fixed-Line') {
        return 'line';
    }
    return 'recursive';
}