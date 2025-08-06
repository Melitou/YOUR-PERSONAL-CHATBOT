import ViewStore from '../stores/ViewStore';

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
            const errorMessage = 'Authentication required - please log in again';
            ViewStore.getState().addError(errorMessage);
            throw new Error(errorMessage);
        }

        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'Unknown error' }));
            const errorMessage = error.message || `Request failed with status ${response.status}`;
            ViewStore.getState().addError(errorMessage);
            throw new Error(errorMessage);
        }

        return response.json();
    }

    async post(endpoint: string, data: any) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'POST',
                headers: this.getAuthHeaders(),
                body: JSON.stringify(data),
            });
            return this.handleResponse(response);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Network error occurred';
            console.error('POST request failed:', errorMessage);
            ViewStore.getState().addError(errorMessage);
            throw error;
        }
    }

    async get(endpoint: string) {
        try {
            const response = await fetch(`${this.baseURL}${endpoint}`, {
                method: 'GET',
                headers: this.getAuthHeaders(),
            });
            return this.handleResponse(response);
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Network error occurred';
            console.error('GET request failed:', errorMessage);
            ViewStore.getState().addError(errorMessage);
            throw error;
        }
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
        try {
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
                const errorMessage = 'Authentication required - please log in again';
                ViewStore.getState().addError(errorMessage);
                throw new Error(errorMessage);
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
                    ViewStore.getState().addError('Failed to parse server error response');
                }
                
                const fullErrorMessage = `Failed to create normal user chatbot: ${errorMessage}`;
                ViewStore.getState().addError(fullErrorMessage);
                throw new Error(fullErrorMessage);
            }

            return response.json();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Network error occurred while creating chatbot';
            console.error('Create normal user chatbot failed:', errorMessage);
            ViewStore.getState().addError(errorMessage);
            throw error;
        }
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

    // Get conversations for a specific chatbot
    getChatbotConversations: (chatbotId: string) =>
        apiClient.get(`/chatbot/${chatbotId}/conversations`),

    // Create a chatbot session
    createChatbotSession: (chatbotId: string) => {
        const formData = new FormData();
        formData.append('chatbot_id', chatbotId);
        return apiClient.post(`/chatbot/${chatbotId}/session`, formData);
    },

    // Create a conversation session
    createConversationSession: (chatbotId: string, conversationId: string) => {
        const formData = new FormData();
        formData.append('conversation_id', conversationId);
        return apiClient.post(`/chatbot/${chatbotId}/conversation/${conversationId}/session`, formData);
    },

    // Create a new conversation (and a session)
    createNewConversationWithSession: (chatbotId: string) => {
        return apiClient.post(`/chatbot/${chatbotId}/conversation/new`, {});
    },
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