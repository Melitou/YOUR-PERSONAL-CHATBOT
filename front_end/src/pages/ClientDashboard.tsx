import React, { useEffect, useState } from 'react';
import { FaEdit, FaTrash } from "react-icons/fa";
import { clientApi, chatbotApi } from '../utils/api';
import ChatComponent from '../components/ChatComponent';
import LoadedChatbotStore, { type ConversationSummary } from '../stores/LoadedChatbotStore';
import ViewStore from '../stores/ViewStore';
import UserAuthStore from '../stores/UserAuthStore';
import EditConversationModalComponent from '../components/EditConversationModalComponent';
import DeleteConversationModalComponent from '../components/DeleteConversationModalComponent';
import ThoughtVisualizerComponent from '../components/ThoughtVisualizerComponent';

interface AssignedChatbot {
    id: string;
    name: string;
    description: string;
    embedding_model: string;
    chunking_method: string;
    date_created: string;
    namespace: string;
    loaded_files: Array<{
        file_name: string;
        file_type: string;
        status: string;
        upload_date: string;
        total_chunks: number;
    }>;
    total_files: number;
    total_chunks: number;
}

const ClientDashboard: React.FC = () => {
    const [assignedChatbots, setAssignedChatbots] = useState<AssignedChatbot[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedChatbot, setSelectedChatbot] = useState<AssignedChatbot | null>(null);

    // Conversation modal states
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState<ConversationSummary | null>(null);
    const [actionLoading, setActionLoading] = useState(false);

    const {
        setLoadedChatbot,
        loadedChatbot,
        loadedChatbotHistory,
        setLoadedChatbotHistory,
        startConversationSession,
        connectToWebSocket,
        createNewConversationWithSession,
        webSocket,
        updateConversationName,
        deleteConversation
    } = LoadedChatbotStore((state: any) => state);
    const { addError, thoughtVisualizerOpen, setThoughtVisualizerOpen } = ViewStore();
    const { user, logout } = UserAuthStore();



    useEffect(() => {
        fetchAssignedChatbots();
    }, []);

    // Load conversations when chatbot is selected
    useEffect(() => {
        if (loadedChatbot) {
            const loadConversations = async () => {
                try {
                    const conversations = await chatbotApi.getChatbotConversations(loadedChatbot.id);
                    setLoadedChatbotHistory(conversations);
                } catch (error) {
                    console.error('Failed to load conversations:', error);
                }
            };
            loadConversations();
        }
    }, [loadedChatbot, webSocket]);

    const fetchAssignedChatbots = async () => {
        try {
            const response = await clientApi.getMyAssignedChatbots();
            setAssignedChatbots(response);

            // Auto-select first chatbot if available
            if (response.length > 0 && !selectedChatbot) {
                handleChatbotSelect(response[0]);
            }
        } catch (error) {
            console.error('Failed to fetch assigned chatbots:', error);
            addError('Failed to load assigned chatbots');
        } finally {
            setLoading(false);
        }
    };

    const handleChatbotSelect = (chatbot: AssignedChatbot) => {
        setSelectedChatbot(chatbot);

        // Transform AssignedChatbot to LoadedChatbot format
        const loadedChatbotData = {
            id: chatbot.id,
            name: chatbot.name,
            description: chatbot.description,
            namespace: chatbot.namespace,
            embeddingModel: chatbot.embedding_model,
            embeddingType: chatbot.embedding_model,
            chunkingProcess: chatbot.chunking_method,
            cloudStorage: 'cloud', // Default value
            files: chatbot.loaded_files.map(file => ({
                id: file.file_name,
                name: file.file_name,
                size: 0, // Not provided in AssignedChatbot
                type: file.file_type,
                uploadedAt: new Date(file.upload_date)
            })),
            isActive: true,
            isThinking: false
        };

        setLoadedChatbot(loadedChatbotData);
    };

    const handleLogout = () => {
        logout();
        window.location.href = '/auth';
    };

    // Conversation handlers
    const handleConversationClick = async (conversation: ConversationSummary) => {
        console.log('Selected conversation:', conversation);
        try {
            // Start conversation session
            const session_id = await startConversationSession(conversation.conversation_id, loadedChatbot.id);
            console.log('Conversation session started successfully:', session_id);
            // Connect to WebSocket
            const ws = await connectToWebSocket(session_id);
            console.log('WebSocket connected successfully:', ws);
        } catch (error) {
            console.error('Failed to start conversation session:', error);
        }
    };

    const handleNewConversationClick = async () => {
        if (!loadedChatbot) {
            addError('Please select a chatbot first');
            return;
        }

        try {
            // Create a new conversation
            const session_id = await createNewConversationWithSession(loadedChatbot.id);
            console.log('New conversation created successfully:', session_id);
            // Connect to WebSocket
            const ws = await connectToWebSocket(session_id);
            console.log('WebSocket connected successfully:', ws);
        } catch (error) {
            console.error('Failed to start new conversation:', error);
            addError('Failed to create new conversation');
        }
    };

    // Handle edit conversation
    const handleEditConversation = (conversation: ConversationSummary, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent conversation click
        setSelectedConversation(conversation);
        setEditModalOpen(true);
    };

    // Handle delete conversation
    const handleDeleteConversation = (conversation: ConversationSummary, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent conversation click
        setSelectedConversation(conversation);
        setDeleteModalOpen(true);
    };

    // Save conversation name
    const handleSaveConversationName = async (newName: string) => {
        if (!selectedConversation) return;
        setActionLoading(true);
        try {
            await updateConversationName(selectedConversation.conversation_id, newName);
        } finally {
            setActionLoading(false);
        }
    };

    // Confirm delete conversation
    const handleConfirmDeleteConversation = async () => {
        if (!selectedConversation) return;
        setActionLoading(true);
        try {
            await deleteConversation(selectedConversation.conversation_id);
        } finally {
            setActionLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="h-screen flex items-center justify-center glass-bg">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <div className="text-lg mt-4 glass-text">Loading your assigned chatbots...</div>
                </div>
            </div>
        );
    }

    if (assignedChatbots.length === 0) {
        return (
            <div className="h-screen flex flex-col glass-bg">
                {/* Header */}
                <div className="glass-card shadow-sm border-b border-gray-200 border-opacity-20 p-4">
                    <div className="flex items-center justify-between max-w-7xl mx-auto">
                        <h1 className="text-xl font-semibold glass-text">My Chatbots</h1>
                        <div className="flex items-center space-x-4">
                            <span className="text-sm glass-text opacity-80">
                                Welcome, {user?.name}!
                            </span>
                            <button
                                onClick={handleLogout}
                                className="px-3 py-1.5 text-sm glass-text hover:glass-light rounded-md transition-colors cursor-pointer"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>

                {/* No chatbots message */}
                <div className="flex-1 flex items-center justify-center">
                    <div className="text-center max-w-md mx-auto p-8">
                        <div className="w-16 h-16 glass-dark rounded-full flex items-center justify-center mx-auto mb-6">
                            <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                            </svg>
                        </div>
                        <h2 className="text-2xl font-semibold mb-4 glass-text">No Chatbots Assigned</h2>
                        <p className="glass-text opacity-70 leading-relaxed">
                            You don't have any chatbots assigned to you yet.
                            Please contact your administrator to get access to chatbots.
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex glass-bg overflow-hidden">
            {/* Sidebar */}
            <aside className="w-80 h-full shadow-lg border-r border-white/20 flex flex-col" style={{ backgroundColor: "#6b846c" }}>
                {/* Chatbot Selector Section */}
                <div className="flex-shrink-0 p-4 border-b border-white/20">
                    <div className="flex items-center mb-4">
                        <h1 className="text-lg font-semibold glass-text">My Chatbots</h1>
                    </div>

                    {/* Chatbot Selector */}
                    {assignedChatbots.length > 0 && (
                        <div className="mb-4">
                            <label htmlFor="chatbot-select" className="text-sm font-medium glass-text mb-2 block">
                                Current Chatbot:
                            </label>
                            <select
                                id="chatbot-select"
                                value={selectedChatbot?.id || ''}
                                onChange={(e) => {
                                    const chatbot = assignedChatbots.find(c => c.id === e.target.value);
                                    if (chatbot) handleChatbotSelect(chatbot);
                                }}
                                className="w-full px-3 py-2 glass-dark rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent glass-text text-sm cursor-pointer"
                            >
                                {assignedChatbots.map(chatbot => (
                                    <option key={chatbot.id} value={chatbot.id}>
                                        {chatbot.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}
                </div>

                {/* Conversations Section */}
                <div className="flex-1 min-h-0 overflow-y-auto p-4">
                    {loadedChatbot ? (
                        <>
                            <div className="mb-4">
                                <h3 className="text-sm font-medium glass-text mb-2">Conversations</h3>
                                <p className="text-xs glass-text opacity-70 mb-3">{loadedChatbot.name}</p>

                                <button
                                    className="w-full p-2 rounded-md glass-dark hover:glass-light glass-text text-sm transition-colors flex items-center justify-center gap-2 cursor-pointer"
                                    onClick={handleNewConversationClick}
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                        <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                                    </svg>
                                    New Conversation
                                </button>
                            </div>

                            <div className="flex flex-col gap-2">
                                {(!loadedChatbotHistory || loadedChatbotHistory.length === 0) ? (
                                    <div className="text-center glass-text opacity-70 text-sm py-4">No conversations yet</div>
                                ) : (
                                    loadedChatbotHistory.map((conversation: ConversationSummary) => {
                                        const conversationTitle = conversation.conversation_title || `Conversation ${conversation.conversation_id.slice(-6)}`;

                                        return (
                                            <div
                                                key={conversation.conversation_id}
                                                className="p-3 rounded-md hover:glass-light cursor-pointer transition-colors group relative"
                                                onClick={() => handleConversationClick(conversation)}
                                            >
                                                <div className="flex items-start gap-2">
                                                    <div className="flex-1 min-w-0 flex flex-col gap-1">
                                                        <div className="truncate glass-text text-sm font-medium">
                                                            {conversationTitle}
                                                        </div>
                                                        <div className="text-xs glass-text opacity-70 flex items-center justify-between">
                                                            <span>Click to open</span>
                                                            <span>{new Date(conversation.created_at).toLocaleDateString()}</span>
                                                        </div>
                                                    </div>

                                                    <div className="flex-none flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                        <button
                                                            onClick={(e) => handleEditConversation(conversation, e)}
                                                            className="p-1.5 hover:bg-blue-500/20 rounded text-blue-400 hover:text-blue-300 transition-colors"
                                                            title="Edit conversation name"
                                                            disabled={actionLoading}
                                                        >
                                                            <FaEdit size={12} />
                                                        </button>
                                                        <button
                                                            onClick={(e) => handleDeleteConversation(conversation, e)}
                                                            className="p-1.5 hover:bg-red-500/20 rounded text-red-400 hover:text-red-300 transition-colors"
                                                            title="Delete conversation"
                                                            disabled={actionLoading}
                                                        >
                                                            <FaTrash size={12} />
                                                        </button>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="text-center glass-text opacity-70 text-sm py-4">
                            Select a chatbot to view conversations
                        </div>
                    )}
                </div>
            </aside>

            {/* Main Content */}
            <div className="flex-1 flex flex-col">
                {/* Header */}
                <div className="glass-card shadow-sm border-b border-gray-200 border-opacity-20 p-4 ml-2.5">
                    <div className="flex items-center justify-between">
                        {/* Chatbot Description */}
                        {selectedChatbot && (
                            <div>
                                <p className="text-sm glass-text opacity-80 leading-relaxed">
                                    {selectedChatbot.description}
                                </p>
                                <div className="flex items-center space-x-4 text-xs glass-text opacity-70 mt-2">
                                    <span className="glass-dark px-2 py-1 rounded">
                                        {selectedChatbot.total_files} files
                                    </span>
                                    <span className="glass-dark px-2 py-1 rounded">
                                        {selectedChatbot.total_chunks} chunks
                                    </span>
                                </div>
                            </div>
                        )}

                        {/* User info and logout - right side */}
                        <div className="flex items-center space-x-4">
                            <span className="text-lg glass-text font-small">
                                Welcome, {user?.name}
                            </span>
                            {/* Thinking Visualizer Toggle */}
                            <button
                                onClick={() => setThoughtVisualizerOpen(!thoughtVisualizerOpen)}
                                className="px-3 py-2 text-sm glass-text hover:glass-light rounded-md transition-colors cursor-pointer flex items-center gap-2"
                                title={thoughtVisualizerOpen ? "Hide AI Thinking" : "Show AI Thinking"}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                                </svg>
                                {thoughtVisualizerOpen ? "Hide Thinking" : "Show Thinking"}
                            </button>
                            <button
                                onClick={handleLogout}
                                className="px-4 py-2 text-base glass-text hover:glass-light rounded-md transition-colors font-small cursor-pointer"
                            >
                                Logout
                            </button>
                        </div>
                    </div>
                </div>

                {/* Chat interface with thinking visualizer */}
                <div className="flex-1 flex p-4 gap-4 min-h-0">
                    {/* Chat Component */}
                    <div className={`${thoughtVisualizerOpen ? 'w-2/3' : 'w-full'} transition-all duration-300 flex flex-col min-h-0`}>
                        {selectedChatbot ? (
                            <div className="h-full flex flex-col min-h-0">
                                <ChatComponent />
                            </div>
                        ) : (
                            <div className="h-full flex items-center justify-center glass-card rounded-lg shadow-sm border border-gray-200 border-opacity-20">
                                <div className="text-center">
                                    <div className="w-12 h-12 glass-dark rounded-full flex items-center justify-center mx-auto mb-4">
                                        <svg className="w-6 h-6 glass-text opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                        </svg>
                                    </div>
                                    <div className="glass-text opacity-70">Select a chatbot to start chatting</div>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Thinking Visualizer - Only show when thoughtVisualizerOpen is true */}
                    {thoughtVisualizerOpen && (
                        <div className="w-1/3 hidden lg:flex flex-col min-h-0">
                            <div className="h-full">
                                <ThoughtVisualizerComponent />
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Edit conversation modal */}
            <EditConversationModalComponent
                open={editModalOpen}
                onClose={() => {
                    setEditModalOpen(false);
                    setSelectedConversation(null);
                }}
                currentName={selectedConversation?.conversation_title || ""}
                onSave={handleSaveConversationName}
                loading={actionLoading}
            />

            {/* Delete conversation modal */}
            <DeleteConversationModalComponent
                open={deleteModalOpen}
                onClose={() => {
                    setDeleteModalOpen(false);
                    setSelectedConversation(null);
                }}
                conversationName={selectedConversation?.conversation_title || ""}
                onConfirm={handleConfirmDeleteConversation}
                loading={actionLoading}
            />
        </div>
    );
};

export default ClientDashboard;
