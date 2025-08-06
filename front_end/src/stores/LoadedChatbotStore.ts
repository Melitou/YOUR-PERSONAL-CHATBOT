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
    setLoadedChatbot: (loadedChatbot: LoadedChatbot) => {
        // Reset conversation state when a new chatbot is loaded
        const state = get() as any;
        if (state.webSocket) {
            state.webSocket.close();
        }
        set({ 
            loadedChatbot,
            conversationMessages: [], // Clear previous conversation
            chatbotSession: null,     // Clear previous session
            webSocket: null,          // Clear WebSocket connection
            isThinking: false         // Reset thinking state
        });
    },

    // The conversations of the chatbot that is loaded
    loadedChatbotHistory: [],
    setLoadedChatbotHistory: (loadedChatbotHistory: ConversationSummary[]) => set({ loadedChatbotHistory }),

    // Current chatbot session
    chatbotSession: null,
    setChatbotSession: (session: ChatbotSession | null) => set({ chatbotSession: session }),

    isThinking: false,
    setIsThinking: (isThinking: boolean) => set({ isThinking }),

    // Conversation messages
    conversationMessages: [],
    setConversationMessages: (conversationMessages: Message[]) => set({ conversationMessages }),

    // WebSocket connection
    webSocket: null,
    setWebSocket: (ws: WebSocket | null) => set({ webSocket: ws }),

    // Start a conversation session and connect via WebSocket
    startConversationSession: async (conversationId: string, chatbotId: string): Promise<string> => {
        try {
            console.log('Starting conversation session for conversationId:', conversationId);
            
            // 1. Disconnect existing WebSocket first
            const state = get() as any;
            if (state.webSocket) {
                state.webSocket.close();
            }
            
            const response = await chatbotApi.createConversationSession(chatbotId, conversationId);
            console.log('Conversation session created successfully:', response);
            set({ chatbotSession: response });
            set({ conversationMessages: response || [] });
            
            return response.session_id; // return the session_id to later connect to WebSocket
        } catch (error) {
            console.error('Failed to start conversation session:', error);
            throw error; // Re-throw to allow caller to handle
        }
    },

    // Create a new conversation (and a session)
    createNewConversationWithSession: async (chatbotId: string) => {
        /*
        This function creates a new conversation and a session id for it.
        It returns the conversation_id to later connect to WebSocket.
        */  
        try {
            const response = await chatbotApi.createNewConversationWithSession(chatbotId);
            console.log('New conversation created successfully:', response);
            
            set({ conversationMessages: response || [] }); // we expect the messages to be empty, because it is a new conversation

            return response.session_id; // return the session_id to later connect to WebSocket
        } catch (error) {
            console.error('Failed to create new conversation:', error);
            throw error;
        }
    },

    connectToWebSocket: async (sessionId: string) => {
        try {
            const userToken = localStorage.getItem('authToken');
            if (!userToken) {
                throw new Error('No authentication token found');
            }
    
            const wsUrl = `ws://localhost:8000/ws/conversation/session/${sessionId}?token=${userToken}`;
            const ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected successfully for session:', sessionId);
                set({ webSocket: ws });
            };
            
            ws.onmessage = (event) => {
                console.log('WebSocket message received:', event.data);
                try {
                    const messageData = JSON.parse(event.data);
                    
                    if (messageData.type === 'session_info') {
                        console.log('Session info received:', messageData);
                    } else if (messageData.type === 'message_received') {
                        console.log('Message acknowledgment received:', messageData);
                    } else if (messageData.type === 'assistant_response_chunk') {
                        // Handle streaming response chunks
                        const currentMessages = get().conversationMessages;
                        const lastMessage = currentMessages[currentMessages.length - 1];
                        
                        if (lastMessage && lastMessage.role === 'agent' && lastMessage.isStreaming) {
                            // Update the last message with new chunk
                            const updatedMessages = [...currentMessages];
                            updatedMessages[updatedMessages.length - 1] = {
                                ...lastMessage,
                                message: lastMessage.message + messageData.chunk
                            };
                            set({ conversationMessages: updatedMessages });
                        } else {
                            // Create new streaming message
                            const newMessage = {
                                message: messageData.chunk,
                                role: 'agent',
                                created_at: new Date().toISOString(),
                                isStreaming: true
                            };
                            set({ conversationMessages: [...currentMessages, newMessage] });
                        }
                    } else if (messageData.type === 'assistant_response_complete') {
                        // Mark streaming as complete
                        const currentMessages = get().conversationMessages;
                        const updatedMessages = currentMessages.map(msg => ({
                            ...msg,
                            isStreaming: false
                        }));
                        set({ conversationMessages: updatedMessages });
                    } else if (messageData.type === 'error') {
                        console.error('WebSocket error message:', messageData.message);
                    }
                } catch (parseError) {
                    console.error('Failed to parse WebSocket message:', parseError);
                }
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                set({ webSocket: null });
            };
            
            ws.onclose = (event) => {
                console.log('WebSocket connection closed:', event.code, event.reason);
                set({ webSocket: null });
            };
            
            return ws;
        } catch (error) {
            console.error('Failed to connect to WebSocket:', error);
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