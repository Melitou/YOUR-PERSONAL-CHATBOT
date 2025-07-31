import { create } from "zustand";
import { agentApi } from "../utils/api";

export interface ChatbotFile {
    id: string;
    name: string;
    size: number;
    type: string;
    uploadedAt: Date;
}

export interface CreatedChatbot {
    id: string;
    name: string;
    description?: string;
    namespace: string;
    index: string;
    embeddingType: 'text-embedding-3-small' | 'text-embedding-3-large' | 'gemini-embedding-001';
    chunkingProcess: 'recursive' | 'semantic' | 'fixed-size';
    files: ChatbotFile[];
    isActive: boolean;
    createdAt: Date;
    updatedAt: Date;
}

interface ChatbotManagerState {
    chatbots: CreatedChatbot[];
    isLoading: boolean;
    error: string | null;
    
    // Actions
    addChatbot: (chatbot: Omit<CreatedChatbot, 'id' | 'createdAt' | 'updatedAt'>) => void;
    updateChatbot: (id: string, updates: Partial<CreatedChatbot>) => void;
    deleteChatbot: (id: string) => void;
    setChatbots: (chatbots: CreatedChatbot[]) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    
    // Utility actions
    getChatbotById: (id: string) => CreatedChatbot | undefined;
    getActiveChatbots: () => CreatedChatbot[];
    toggleChatbotStatus: (id: string) => void;
    
    // API integration actions
    fetchChatbots: () => Promise<void>;
    createChatbot: (data: Omit<CreatedChatbot, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
    removeChatbot: (id: string) => Promise<void>;
}

const ChatbotManagerStore = create<ChatbotManagerState>((set, get) => ({
    chatbots: [],
    isLoading: false,
    error: null,

    // Basic state management
    addChatbot: (chatbotData) => {
        const newChatbot: CreatedChatbot = {
            ...chatbotData,
            id: crypto.randomUUID(),
            createdAt: new Date(),
            updatedAt: new Date(),
        };
        
        set((state) => ({
            chatbots: [...state.chatbots, newChatbot],
            error: null
        }));
    },

    updateChatbot: (id, updates) => {
        set((state) => ({
            chatbots: state.chatbots.map(chatbot =>
                chatbot.id === id
                    ? { ...chatbot, ...updates, updatedAt: new Date() }
                    : chatbot
            ),
            error: null
        }));
    },

    deleteChatbot: (id) => {
        set((state) => ({
            chatbots: state.chatbots.filter(chatbot => chatbot.id !== id),
            error: null
        }));
    },

    setChatbots: (chatbots) => {
        set({ chatbots, error: null });
    },

    setLoading: (isLoading) => {
        set({ isLoading });
    },

    setError: (error) => {
        set({ error, isLoading: false });
    },

    // Utility functions
    getChatbotById: (id) => {
        return get().chatbots.find(chatbot => chatbot.id === id);
    },

    getActiveChatbots: () => {
        return get().chatbots.filter(chatbot => chatbot.isActive);
    },

    toggleChatbotStatus: (id) => {
        const { updateChatbot, getChatbotById } = get();
        const chatbot = getChatbotById(id);
        if (chatbot) {
            updateChatbot(id, { isActive: !chatbot.isActive });
        }
    },

    // API integration methods
    fetchChatbots: async () => {
        try {
            set({ isLoading: true, error: null });
            
            const response = await agentApi.getUserAgents();
            set({ chatbots: response.data || [], isLoading: false });
        } catch (error) {
            console.error('Failed to fetch chatbots:', error);
            set({ 
                error: error instanceof Error ? error.message : 'Failed to fetch chatbots',
                isLoading: false 
            });
        }
    },

    createChatbot: async (data) => {
        try {
            set({ isLoading: true, error: null });
            
            // Map the data to match the API expected format
            const apiData = {
                name: data.name,
                description: data.description || '',
                aiProvider: data.embeddingType,
                files: data.files.map(f => f as any) // Convert ChatbotFile to File type
            };
            
            const response = await agentApi.createUserAgent(apiData);
            
            // Add the created chatbot to local state
            if (response.data) {
                get().addChatbot(data);
            }
            
            set({ isLoading: false });
        } catch (error) {
            console.error('Failed to create chatbot:', error);
            set({ 
                error: error instanceof Error ? error.message : 'Failed to create chatbot',
                isLoading: false 
            });
        }
    },

    removeChatbot: async (id) => {
        try {
            set({ isLoading: true, error: null });
            
            await agentApi.deleteAgent(id);
            
            // Remove from local state on successful deletion
            get().deleteChatbot(id);
            set({ isLoading: false });
        } catch (error) {
            console.error('Failed to delete chatbot:', error);
            set({ 
                error: error instanceof Error ? error.message : 'Failed to delete chatbot',
                isLoading: false 
            });
        }
    },
}));

export default ChatbotManagerStore;