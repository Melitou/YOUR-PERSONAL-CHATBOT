import { useEffect, useState } from "react";
import { FaBars, FaTimes } from "react-icons/fa";
//import UserComponent from "./UserComponent";    
import CreateBotUserModalComponent from "./CreateBotUserModalComponent";
import CreateBotSuperUserModalComponent from "./CreateBotSuperUserModalComponent";
import UserAuthStore from "../stores/UserAuthStore";
import ManageChatbotsModalComponent from "./ManageChatbotsModalComponent";
import LoadedChatbotStore, { type ConversationSummary } from "../stores/LoadedChatbotStore";
import { chatbotApi } from "../utils/api";

const SidebarComponent = () => {
    const user = UserAuthStore((state: any) => state.user);
    const { loadedChatbot, loadedChatbotHistory, startConversationSession, setLoadedChatbotHistory, connectToWebSocket, createNewConversationWithSession, webSocket } = LoadedChatbotStore((state: any) => state);

    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [createBotModalOpen, setCreateBotModalOpen] = useState(false);
    const [existingChatbotsModalOpen, setExistingChatbotsModalOpen] = useState(false);

    const handleNewChatbotClick = () => {
        // Open the create bot modal
        setCreateBotModalOpen(true);
    }

    const handleExistingChatbotsClick = () => {
        // Open the existing chatbots modal
        setExistingChatbotsModalOpen(true);
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
            {/* Hamburger button for mobile */}
            <button
                className="fixed top-4 left-4 z-50 sm:hidden bg-gray-800 text-white p-2 rounded-md shadow-lg"
                onClick={() => setSidebarOpen(true)}
                aria-label="Open sidebar"
            >
                <FaBars size={24} />
            </button>

            <aside
                className={`
                    fixed top-0 left-0 h-screen w-64 bg-[#f9f9f9] z-40 transform
                    ${sidebarOpen ? "translate-x-0" : "-translate-x-full"}
                    transition-transform duration-300
                    sm:translate-x-0 sm:static sm:h-screen
                    shadow-lg
                    flex flex-col
                `}
                style={{ boxSizing: "border-box" }}
            >
                {/* Close button for mobile */}
                <button
                    className="absolute top-4 right-4 sm:hidden text-black z-50"
                    onClick={() => setSidebarOpen(false)}
                    aria-label="Close sidebar"
                >
                    <FaTimes size={24} />
                </button>

                {/* Chatbots action buttons */}
                <div className="flex-shrink-0 p-3 pt-16 sm:pt-3 border-b border-gray-200 flex flex-col gap-2">
                    <button className="p-3 w-full rounded-md hover:bg-[#efefef] transition-colors flex items-center justify-start gap-2 text-black text-xs sm:text-sm" onClick={handleNewChatbotClick}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd" />
                        </svg>
                        New Chatbot
                    </button>
                    <button className="p-3 w-full rounded-md hover:bg-[#efefef] transition-colors flex items-center justify-start gap-2 text-black text-xs sm:text-sm" onClick={handleExistingChatbotsClick}>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
                        </svg>
                        Manage Chatbots
                    </button>
                </div>

                {/* Scrollable chatbot conversation history list */}
                <div className="flex-1 min-h-0 overflow-y-auto pt-3 px-3 pb-3">
                    {loadedChatbot && (
                        <div className="mb-3">
                            <div className="px-2 mb-2">
                                <h3 className="text-sm font-medium text-gray-700 mb-1">Conversations</h3>
                                <p className="text-xs text-gray-500">{loadedChatbot.name}</p>
                            </div>
                            <button 
                                className="w-full p-2 mb-3 rounded-md bg-black hover:bg-gray-800 text-white text-sm transition-colors flex items-center justify-center gap-2"
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
                            <div className="text-center text-gray-500 text-xs sm:text-sm px-2 py-4">No conversations yet</div>
                        )}
                        {!loadedChatbot && (
                            <div className="text-center text-gray-500 text-xs sm:text-sm px-2 py-4">Select a chatbot to view conversations</div>
                        )}
                        {loadedChatbotHistory && loadedChatbotHistory.map((conversation: ConversationSummary) => {
                            // Use the conversation_title from the session response
                            const conversationTitle = conversation.conversation_title || `Conversation ${conversation.conversation_id.slice(-6)}`;
                            
                            return (
                                <div 
                                    key={conversation.conversation_id} 
                                    className="p-3 rounded-md hover:bg-[#efefef] cursor-pointer transition-colors group"
                                    onClick={() => handleConversationClick(conversation)}
                                >
                                    <div className="flex flex-col gap-1">
                                        <div className="truncate text-black text-sm font-medium">
                                            {conversationTitle}
                                        </div>
                                        <div className="text-xs text-gray-500 flex items-center justify-between">
                                            <span>Click to open</span>
                                            <span>{new Date(conversation.created_at).toLocaleDateString()}</span>
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

            {/* Overlay for mobile when sidebar is open */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black bg-opacity-40 z-30 sm:hidden"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

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
                onSelectChatbot={() => {}}
            />
        </> 
    );
}

export default SidebarComponent;