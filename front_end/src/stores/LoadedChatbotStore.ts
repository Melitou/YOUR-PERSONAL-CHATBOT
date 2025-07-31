import { create } from "zustand";

// Manage the chatbot state that is loaded

export interface LoadedChatbot {
    id: string;
    name: string;
    description: string;
    files: File[];
    namespace: string;
    chunkingProcess: string;
    cloudStorage: string;
    embeddingModel: string;
    embeddingType: string;
    isActive: boolean; // When a chatbot is loaded, it is set to true else false
    isThinking: boolean; // When a chatbot is thinking, it is set to true else false
}

const LoadedChatbotStore = create((set) => ({
    loadedChatbot: null,
    setLoadedChatbot: (loadedChatbot: LoadedChatbot) => set({ loadedChatbot }),

    // The conversations of the chatbot that is loaded
    loadedChatbotHistory: [],
    setLoadedChatbotHistory: (loadedChatbotHistory: LoadedChatbot[]) => set({ loadedChatbotHistory }),

    isThinking: false,
    setIsThinking: (isThinking: boolean) => set({ isThinking }),
}));

export default LoadedChatbotStore;