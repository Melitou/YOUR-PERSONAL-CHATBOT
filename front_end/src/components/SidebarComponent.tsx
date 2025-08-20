import { useEffect, useState } from "react";
import { FaTimes, FaEdit, FaTrash } from "react-icons/fa";
//import UserComponent from "./UserComponent";    
import CreateBotUserModalComponent from "./CreateBotUserModalComponent";
import CreateBotSuperUserModalComponent from "./CreateBotSuperUserModalComponent";
import EditConversationModalComponent from "./EditConversationModalComponent";
import DeleteConversationModalComponent from "./DeleteConversationModalComponent";
import UserAuthStore from "../stores/UserAuthStore";
import ViewStore from "../stores/ViewStore";
import ManageChatbotsModalComponent from "./ManageChatbotsModalComponent";

import LoadedChatbotStore, { type ConversationSummary } from "../stores/LoadedChatbotStore";
import { chatbotApi } from "../utils/api";

const SidebarComponent = () => {
    const user = UserAuthStore((state: any) => state.user);
    const { loadedChatbot, loadedChatbotHistory, startConversationSession, setLoadedChatbotHistory, connectToWebSocket, createNewConversationWithSession, webSocket, updateConversationName, deleteConversation } = LoadedChatbotStore((state: any) => state);
    const { setSidebarOpen, setCurrentView } = ViewStore();

    const [createBotModalOpen, setCreateBotModalOpen] = useState(false);
    const [existingChatbotsModalOpen, setExistingChatbotsModalOpen] = useState(false);

    // Modal states for conversation editing and deleting
    const [editModalOpen, setEditModalOpen] = useState(false);
    const [deleteModalOpen, setDeleteModalOpen] = useState(false);
    const [selectedConversation, setSelectedConversation] = useState<ConversationSummary | null>(null);
    const [actionLoading, setActionLoading] = useState(false);


    const handleNewChatbotClick = () => {
        // Open the create bot modal
        setCreateBotModalOpen(true);
    }

    const handleExistingChatbotsClick = () => {
        // Open the existing chatbots modal
        setExistingChatbotsModalOpen(true);
    }

    const handleManageClientsClick = () => {
        // Navigate to organizations page
        setCurrentView('organizations');
    }

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
    }

    const handleNewConversationClick = async () => {
        try {
            // Create a new conversation
            const session_id = await createNewConversationWithSession(loadedChatbot.id);
            console.log('New conversation created successfully:', session_id);
            // Connect to WebSocket
            const ws = await connectToWebSocket(session_id);
            console.log('WebSocket connected successfully:', ws);
        } catch (error) {
            console.error('Failed to start new conversation:', error);
        }
    }

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

    useEffect(() => {
        if (loadedChatbot) {
            // Load the conversations of the chatbot selected
            const loadConversations = async () => {
                const conversations = await chatbotApi.getChatbotConversations(loadedChatbot.id);
                setLoadedChatbotHistory(conversations);
            }
            loadConversations();
        }
    }, [loadedChatbot, webSocket]);

    return (
        <>
            <aside
                className={`
                    h-full w-full z-40
                    shadow-lg border-r border-white/20
                    flex flex-col
                `}
                style={{
                    boxSizing: "border-box",
                    backgroundColor: "#6b846c"
                }}
            >
                {/* Close button for mobile */}
                <button
                    className="absolute top-4 right-4 lg:hidden glass-text z-50"
                    onClick={() => setSidebarOpen(false)}
                    aria-label="Close sidebar"
                >
                    <FaTimes size={24} />
                </button>

                {/* Chatbots action buttons */}
                <div className="flex-shrink-0 p-3 pt-16 lg:pt-3 border-b border-white/20 flex flex-col gap-2">
                    <button className="p-3 w-full rounded-md hover:glass-light transition-colors flex items-center justify-start gap-2 glass-text text-xs sm:text-sm" onClick={handleNewChatbotClick}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                        </svg>
                        New Chatbot
                    </button>
                    <button className="p-3 w-full rounded-md hover:glass-light transition-colors flex items-center justify-start gap-2 glass-text text-xs sm:text-sm" onClick={handleExistingChatbotsClick}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                        </svg>
                        Manage Chatbots
                    </button>
                    {/* Super User only button for managing clients */}
                    {user?.role === 'Super User' && (
                        <button className="p-3 w-full rounded-md hover:glass-light transition-colors flex items-center justify-start gap-2 glass-text text-xs sm:text-sm" onClick={handleManageClientsClick}>
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                            </svg>
                            Manage Clients
                        </button>
                    )}
                </div>

                {/* Scrollable chatbot conversation history list */}
                <div className="flex-1 min-h-0 overflow-y-auto pt-3 px-3 pb-3">
                    {loadedChatbot && (
                        <div className="mb-3">
                            <div className="px-2 mb-2">
                                <h3 className="text-sm font-medium glass-text mb-1">Conversations</h3>
                                <p className="text-xs glass-text opacity-70">{loadedChatbot.name}</p>
                            </div>
                            <button
                                className="w-full p-2 mb-3 rounded-md glass-dark hover:glass-light glass-text text-sm transition-colors flex items-center justify-center gap-2"
                                onClick={handleNewConversationClick}
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                    <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
                                </svg>
                                New Conversation
                            </button>
                        </div>
                    )}
                    <div className="flex flex-col gap-2">
                        {(!loadedChatbotHistory || loadedChatbotHistory.length === 0) && loadedChatbot && (
                            <div className="text-center glass-text opacity-70 text-xs sm:text-sm px-2 py-4">No conversations yet</div>
                        )}
                        {!loadedChatbot && (
                            <div className="text-center glass-text opacity-70 text-xs sm:text-sm px-2 py-4">Select a chatbot to view conversations</div>
                        )}
                        {loadedChatbotHistory && loadedChatbotHistory.map((conversation: ConversationSummary) => {
                            // Use the conversation_title from the session response
                            const conversationTitle = conversation.conversation_title || `Conversation ${conversation.conversation_id.slice(-6)}`;

                            return (
                                <div
                                    key={conversation.conversation_id}
                                    className="p-3 rounded-md hover:glass-light cursor-pointer transition-colors group relative"
                                    onClick={() => handleConversationClick(conversation)}
                                >
                                    <div className="flex items-start gap-2">
                                        {/* Conversation content */}
                                        <div className="flex-1 min-w-0 flex flex-col gap-1">
                                            <div className="truncate glass-text text-sm font-medium">
                                                {conversationTitle}
                                            </div>
                                            <div className="text-xs glass-text opacity-70 flex items-center justify-between">
                                                <span>Click to open</span>
                                                <span>{new Date(conversation.created_at).toLocaleDateString()}</span>
                                            </div>
                                        </div>

                                        {/* Action buttons - visible on hover */}
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
                        })}
                    </div>
                </div>

                {/* User settings section */}
                {/* <UserComponent /> */}
            </aside>



            {/* Show appropriate modal based on permissions (frontend convenience only) */}
            {/* Backend will still verify permissions on API calls */}
            {user?.role === 'Super User' ? (
                <CreateBotSuperUserModalComponent
                    open={createBotModalOpen}
                    onClose={() => setCreateBotModalOpen(false)}
                />
            ) : (
                <CreateBotUserModalComponent
                    open={createBotModalOpen}
                    onClose={() => setCreateBotModalOpen(false)}
                />
            )}

            {/* Manage chatbots modal */}
            <ManageChatbotsModalComponent
                open={existingChatbotsModalOpen}
                onClose={() => setExistingChatbotsModalOpen(false)}
                onSelectChatbot={() => { }}
            />

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

        </>
    );
}

export default SidebarComponent;