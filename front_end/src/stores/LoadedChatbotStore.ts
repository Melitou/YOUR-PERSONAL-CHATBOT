import { create } from "zustand";
import { chatbotApi } from "../utils/api";

// Manage the chatbot state that is loaded

export interface Message {
    message: string;
    created_at: string;
    role: 'user' | 'agent';
}

export interface Conversation {
    conversation_id: string;
    messages?: Message[];
    created_at: string;
    belonging_user_uid: string;
    belonging_chatbot_id: string;
}

export interface ConversationSummary {
    conversation_id: string;
    conversation_title: string;
    created_at: string;
    belonging_user_uid: string;
    belonging_chatbot_id: string;
}

export interface ChatbotSession {
    session_id: string;
    chatbot_id: string;
    chatbot_name: string;
    conversations: ConversationSummary[];
}

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

const LoadedChatbotStore = create((set, get) => ({
    loadedChatbot: null,
    setLoadedChatbot: (loadedChatbot: LoadedChatbot) => set({ loadedChatbot }),

    // The conversations of the chatbot that is loaded
    loadedChatbotHistory: [],
    setLoadedChatbotHistory: (loadedChatbotHistory: ConversationSummary[]) => set({ loadedChatbotHistory }),

    // Current chatbot session
    chatbotSession: null,
    setChatbotSession: (session: ChatbotSession | null) => set({ chatbotSession: session }),

    // WebSocket connection
    webSocket: null,
    setWebSocket: (ws: WebSocket | null) => set({ webSocket: ws }),

    isThinking: false,
    setIsThinking: (isThinking: boolean) => set({ isThinking }),

    // Conversation messages
    conversationMessages: [],
    setConversationMessages: (conversationMessages: Message[]) => set({ conversationMessages }),

    // Fetch conversation messages
    fetchConversationMessages: async (conversationId: string) => {
        try {
            console.log('Fetching conversation messages for conversationId:', conversationId);
            const messages = await chatbotApi.getConversationMessages(conversationId);
            console.log('Conversation messages fetched successfully:', messages);
            set({ conversationMessages: messages || [] });
            return messages;
        } catch (error) {
            console.error('Failed to fetch conversation messages:', error);
            set({ conversationMessages: [] });
            throw error;
        }
    },

    // Create a chatbot session and connect via WebSocket
     createChatbotSession: async (chatbotId: string) => {
         try {
             console.log('Creating chatbot session for chatbotId:', chatbotId);
             
             const response: ChatbotSession = await chatbotApi.createChatbotSession(chatbotId);
             console.log('Chatbot session created successfully:', response);
             
             // Store the session
             set({ chatbotSession: response });
             
             // Update conversation history with session conversations
             set({ loadedChatbotHistory: response.conversations || [] });
             
             // Connect to WebSocket
             const userToken = localStorage.getItem('authToken');
             if (userToken) {
                 const wsUrl = `ws://localhost:8000/ws/chat/${response.session_id}?token=${userToken}`;
                 const ws = new WebSocket(wsUrl);
                 
                 ws.onopen = () => {
                     console.log('WebSocket connected successfully');
                     set({ webSocket: ws });
                 };
                 
                 ws.onmessage = (event) => {
                     console.log('WebSocket message received:', event.data);
                     // TODO: Handle incoming messages
                 };
                 
                 ws.onerror = (error) => {
                     console.error('WebSocket error:', error);
                 };
                 
                 ws.onclose = () => {
                     console.log('WebSocket connection closed');
                     set({ webSocket: null });
                 };
             }
             
             return response;
         } catch (error) {
             console.error('Failed to create chatbot session:', error);
             throw error;
         }
     },

     // Disconnect WebSocket
     disconnectWebSocket: () => {
         const state = get() as any;
         if (state.webSocket) {
             state.webSocket.close();
             set({ webSocket: null });
         }
     },

     // Send message via WebSocket
     sendMessage: (message: string) => {
         const state = get() as any;
         if (state.webSocket && state.webSocket.readyState === WebSocket.OPEN) {
             const messageData = {
                 message: message,
                 timestamp: new Date().toISOString()
             };
             state.webSocket.send(JSON.stringify(messageData));
             console.log('Message sent:', messageData);
             return true;
         } else {
             console.error('WebSocket is not connected');
             return false;
         }
     },

    resetStore: () => {
        const state = get() as any;
        if (state.webSocket) {
            state.webSocket.close();
        }
        set({
            loadedChatbot: null,
            loadedChatbotHistory: [],
            chatbotSession: null,
            webSocket: null,
            isThinking: false,
        });
    },
}));

export default LoadedChatbotStore;