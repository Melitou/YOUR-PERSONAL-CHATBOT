import { create } from "zustand";
import { chatbotApi } from "../utils/api";

// Manage the chatbot state that is loaded

export interface Message {
    message: string;
    created_at: string;
    role: 'user' | 'agent';
    isStreaming?: boolean; // Optional flag for streaming messages
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
            conversationMessages: null, // Clear previous conversation
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

    // Conversation messages (complete conversation object)
    conversationMessages: null,
    setConversationMessages: (conversationMessages: Conversation | null) => set({ conversationMessages }),

    // Handle the streaming chunk received
    // This corresponds to ONE agent response message
    handleStreamingChunk: (chunk: string) => {
        const state = get() as any;
        const conversation = state.conversationMessages;
        const currentMessages = [...(conversation?.messages || [])];
        
        // Check if the last message is an agent message that's still being built
        const lastMessage = currentMessages[currentMessages.length - 1];
        
        if (lastMessage && lastMessage.role === 'agent' && lastMessage.isStreaming) {
            // Append to existing streaming message
            lastMessage.message += chunk;
            set({ conversationMessages: { ...conversation, messages: currentMessages } });
        } else {
            // Create a new agent message for streaming
            const newMessage: Message = {
                message: chunk,
                created_at: new Date().toISOString(),
                role: 'agent',
                isStreaming: true
            };
            currentMessages.push(newMessage);
            set({ conversationMessages: { ...conversation, messages: currentMessages } });
        }
    },

    // Complete the streaming agent response
    completeStreamingResponse: (_messageId: string, timestamp: string, fullResponse: string) => {
        const state = get() as any;
        const conversation = state.conversationMessages;
        const currentMessages = [...(conversation?.messages || [])];
        
        // Find and update the last agent message that was streaming
        const lastMessage = currentMessages[currentMessages.length - 1];
        if (lastMessage && lastMessage.role === 'agent' && lastMessage.isStreaming) {
            lastMessage.message = fullResponse;
            lastMessage.created_at = timestamp;
            // Don't remove streaming flag yet - let the UI component handle it
            // The UI will remove isStreaming when animation completes
        }
        
        set({ 
            conversationMessages: { ...conversation, messages: currentMessages },
            isThinking: false 
        });
    },

    // Mark streaming as complete (called by UI when animation finishes)
    markStreamingComplete: () => {
        const state = get() as any;
        const conversation = state.conversationMessages;
        const currentMessages = [...(conversation?.messages || [])];
        
        // Find and update the last agent message that was streaming
        const lastMessage = currentMessages[currentMessages.length - 1];
        if (lastMessage && lastMessage.role === 'agent' && lastMessage.isStreaming) {
            delete lastMessage.isStreaming; // Remove streaming flag
        }
        
        set({ 
            conversationMessages: { ...conversation, messages: currentMessages }
        });
    },

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
            set({ chatbotSession: response });
            set({ conversationMessages: response });
            
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
            
            set({ conversationMessages: response }); // we expect the messages to be empty, because it is a new conversation

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
                set({ webSocket: ws });
            };
            
            ws.onmessage = (event) => {
                try {
                    const messageData = JSON.parse(event.data);
                    
                    if (messageData.type === 'response_chunk') { // Streaming response chunks
                        const state = get() as any;
                        state.handleStreamingChunk(messageData.chunk);
                    } else if (messageData.type === 'response_complete') { // The response is complete
                        const state = get() as any;
                        state.completeStreamingResponse(
                            messageData.message_id,
                            messageData.timestamp,
                            messageData.full_response
                        );

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
            
            ws.onclose = () => {
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
             // Add user message to conversation immediately
             const userMessage: Message = {
                 message: message,
                 created_at: new Date().toISOString(),
                 role: 'user'
             };
             
             const conversation = state.conversationMessages;
             const currentMessages = [...(conversation?.messages || [])];
             currentMessages.push(userMessage);
             set({ 
                 conversationMessages: { ...conversation, messages: currentMessages },
                 isThinking: true // Set thinking state while waiting for response
             });

             const messageData = {
                 message: message,
                 timestamp: new Date().toISOString()
             };
                         state.webSocket.send(JSON.stringify(messageData));
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
            conversationMessages: null,
            webSocket: null,
            isThinking: false,
        });
    },
}));

export default LoadedChatbotStore;