import { create } from "zustand";
import { chatbotApi } from "../utils/api";

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
    
    // API integration actions
    fetchChatbots: () => Promise<void>;
    createChatbotSuperUser: (data: any) => Promise<void>;
    createChatbotNormalUser: (data: any) => Promise<void>;
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



    // API integration methods
    fetchChatbots: async () => {
        try {
            set({ isLoading: true, error: null });
            
            const response = await chatbotApi.getUserChatbots();
            
            // Transform backend data to frontend format
            const transformedChatbots: CreatedChatbot[] = (response || []).map((chatbot: any) => ({
                id: chatbot.id,
                name: chatbot.name,
                description: chatbot.description,
                namespace: chatbot.namespace,
                index: chatbot.namespace, // Use namespace as index for now
                embeddingType: chatbot.embedding_model as 'text-embedding-3-small' | 'text-embedding-3-large' | 'gemini-embedding-001',
                chunkingProcess: chatbot.chunking_method as 'recursive' | 'semantic' | 'fixed-size',
                files: (chatbot.loaded_files || []).map((file: any) => ({
                    id: file.file_name, // Use filename as ID for now
                    name: file.file_name,
                    size: 0, // Backend doesn't provide file size
                    type: file.file_type === 'txt' ? 'text/plain' : 'application/octet-stream',
                    uploadedAt: new Date(file.upload_date)
                })),
                isActive: true, // Default to true since backend doesn't provide this
                createdAt: new Date(chatbot.date_created),
                updatedAt: new Date(chatbot.date_created), // Backend doesn't have updated date
            }));
            
            set({ chatbots: transformedChatbots, isLoading: false });
        } catch (error) {
            console.error('Failed to fetch chatbots:', error);
            set({ 
                error: error instanceof Error ? error.message : 'Failed to fetch chatbots',
                isLoading: false 
            });
        }
    },

    createChatbotSuperUser: async (data) => {
        try {
            set({ isLoading: true, error: null });
            
            // Map the data to match the API expected format
            const apiData = {
                user_namespace: data.name,
                agent_description: data.description,
                agent_provider: '',
                chunking_method: data.chunkingMethod,
                embedding_model: data.embeddingModel,
                files: data.files.map((f: any) => f as any) // Convert ChatbotFile to File type
            };
            
            const response = await chatbotApi.createSuperUserChatbot(
                apiData.user_namespace, 
                apiData.agent_description, 
                apiData.files, 
                apiData.chunking_method, 
                apiData.embedding_model
            );
            
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

    createChatbotNormalUser: async (data) => {
        try {
            set({ isLoading: true, error: null });

            const apiData = {
                user_namespace: data.name,
                agent_description: data.description,
                agent_provider: data.agent_provider,
                chunking_method: '',
                embedding_model: '',
                files: data.files.map((f: any) => f as any) // Convert ChatbotFile to File type
            };

            const response = await chatbotApi.createNormalUserChatbot(
                apiData.user_namespace,
                apiData.agent_description,
                apiData.files,
                apiData.agent_provider
            );
    
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