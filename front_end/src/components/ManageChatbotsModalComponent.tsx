import { Modal } from "@mui/material";
import { useState, useEffect } from "react";
import { chatbotApi } from "../utils/api";

import ChatbotManagerStore, { type CreatedChatbot } from "../stores/ChatbotManagerStore";
import LoadedChatbotStore from "../stores/LoadedChatbotStore";
import ViewStore from "../stores/ViewStore";

const ManageChatbotsModalComponent = ({ 
    open, 
    onClose,
    onSelectChatbot
}: { 
    open: boolean, 
    onClose: () => void,
    onSelectChatbot?: (chatbot: CreatedChatbot) => void
}) => {
    const { 
        chatbots, 
        isLoading, 
        error,
        fetchChatbots,
        removeChatbot
    } = ChatbotManagerStore();
    const [expandedChatbot, setExpandedChatbot] = useState<string | null>(null);
    const [health, setHealth] = useState<Record<string, { ready: boolean; vectors: number }>>({});
    const { setLoadedChatbot } = LoadedChatbotStore((state: any) => state);
    const { addError } = ViewStore();

    // Fetch real chatbots when modal opens
    useEffect(() => {
        if (open) {
            fetchChatbots().catch((error) => {
                const errorMsg = 'Failed to load chatbots';
                addError(errorMsg);
            });
        }
    }, [open, fetchChatbots, addError]);

    // Fetch health for expanded chatbot
    useEffect(() => {
        const id = expandedChatbot;
        if (!id) return;
        let cancelled = false;
        const fetchHealth = async () => {
            try {
                const res = await chatbotApi.getChatbotHealth(id);
                if (!cancelled) {
                    setHealth((h) => ({ ...h, [id]: { ready: Boolean(res.ready), vectors: Number(res.pinecone_vectors || 0) } }));
                }
            } catch {
                // ignore; badge will stay unknown
            }
        };
        fetchHealth();
        const t = setInterval(fetchHealth, 3000);
        return () => { cancelled = true; clearInterval(t); };
    }, [expandedChatbot]);

    // Also fetch health for all chatbots when list loads, so pills don't stay in "Preparing…"
    useEffect(() => {
        if (!open || !chatbots || chatbots.length === 0) return;
        let cancelled = false;
        const loadAll = async () => {
            try {
                const entries = await Promise.all(chatbots.map(async (c) => {
                    try {
                        const res = await chatbotApi.getChatbotHealth(c.id);
                        return [c.id, { ready: Boolean(res.ready), vectors: Number(res.pinecone_vectors || 0) }] as const;
                    } catch {
                        return [c.id, { ready: false, vectors: 0 }] as const;
                    }
                }));
                if (!cancelled) {
                    setHealth(Object.fromEntries(entries));
                }
            } catch {/* ignore */}
        };
        loadAll();
        const t = setInterval(loadAll, 10000);
        return () => { cancelled = true; clearInterval(t); };
    }, [open, chatbots]);

    const getFileIcon = (type: string) => {
        if (type.includes('pdf')) return { icon: 'picture_as_pdf', color: 'text-red-500' };
        if (type.includes('word') || type.includes('document')) return { icon: 'description', color: 'text-blue-500' };
        if (type.includes('csv')) return { icon: 'table_chart', color: 'text-green-500' };
        if (type.includes('markdown')) return { icon: 'code', color: 'text-purple-500' };
        if (type.includes('text')) return { icon: 'description', color: 'text-gray-500' };
        if (type.includes('image')) return { icon: 'image', color: 'text-yellow-500' };
        if (type.includes('excel') || type.includes('spreadsheet')) return { icon: 'table_chart', color: 'text-green-600' };
        return { icon: 'insert_drive_file', color: 'text-gray-400' };
    };

    const toggleExpanded = (chatbotId: string) => {
        setExpandedChatbot(expandedChatbot === chatbotId ? null : chatbotId);
    };

    const handleSelectChatbot = async (chatbot: CreatedChatbot) => {
        setLoadedChatbot(chatbot);
        
        if (onSelectChatbot) {
            onSelectChatbot(chatbot);
        }

        onClose();
    };

    const handleDeleteChatbot = async (e: React.MouseEvent, chatbotId: string, chatbotName: string) => {
        e.stopPropagation();
        
        if (window.confirm(`Are you sure you want to delete "${chatbotName}"? This action cannot be undone.`)) {
            try {
                await removeChatbot(chatbotId);
            } catch (error) {
                const errorMsg = `Failed to delete chatbot "${chatbotName}"`;
                console.error('Delete chatbot error:', error);
                addError(errorMsg);
            }
        }
    };

    return (
        <Modal
            open={open}
            onClose={onClose}
            sx={{
                backdropFilter: 'blur(5px)',
                backgroundColor: 'rgba(0, 0, 0, 0.5)'
            }}
        >
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90%] sm:w-[70%] h-[90%] sm:h-[70%] bg-white rounded-lg shadow-lg p-2 sm:p-8 flex flex-row gap-6">
                <div className="flex flex-col gap-6 flex-1 w-[70%]">
                    {/* Header */}
                    <div className="border-b border-gray-200 px-2 sm:px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div className="flex flex-col items-start space-x-4">
                                <h2 className="text-lg sm:text-xl font-semibold text-gray-900">
                                    My Chatbots ({chatbots.length})
                                </h2>
                                <span className="text-xs sm:text-sm text-gray-500">
                                    Real-time Data
                                </span>
                            </div>
                            <button
                                onClick={onClose}
                                className="text-gray-400 hover:text-gray-600 transition-colors text-xs sm:text-sm"
                            >
                                <span className="material-symbols-outlined text-xs sm:text-sm">close</span>
                            </button>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="overflow-y-auto overflow-x-hidden max-h-[calc(80vh-120px)]">
                        {/* Loading State */}
                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6">
                                <p className="text-gray-500 text-center text-xs sm:text-sm">Loading chatbots...</p>
                            </div>
                        ) : 
                        /* Error State */
                        error ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6">
                                <span className="material-symbols-outlined text-6xl text-red-300 mb-4 text-center">
                                    error
                                </span>
                                <h3 className="text-lg font-medium text-gray-900 mb-2 text-xs sm:text-sm">
                                    Error loading chatbots
                                </h3>
                                <p className="text-gray-500 text-center mb-4 text-xs sm:text-sm">
                                    {error}
                                </p>
                            </div>
                        ) : 
                        /* Empty State */
                        chatbots.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6">
                                <span className="material-symbols-outlined text-6xl text-gray-300 mb-4 text-center">
                                    smart_toy
                                </span>
                                <h3 className="text-lg font-medium text-gray-900 mb-2 text-xs sm:text-sm">
                                    No chatbots yet
                                </h3>
                                <p className="text-gray-500 text-center text-xs sm:text-sm">
                                    Create your first chatbot to get started with AI assistance.
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
                                {chatbots.map((chatbot) => (
                                    <div key={chatbot.id} className="p-2 sm:p-6">
                                        {/* Chatbot List Item */}
                                        <div 
                                            className="cursor-pointer hover:bg-gray-50 p-2 sm:p-4 rounded-lg transition-colors"
                                            onClick={() => toggleExpanded(chatbot.id)}
                                        >
                                            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 w-full">
                                                <div className="flex items-start sm:items-center gap-3 sm:gap-4 w-full min-w-0">
                                                    <div className={`w-8 h-8 sm:w-12 sm:h-12 rounded-full flex items-center justify-center ${
                                                        chatbot.isActive ? 'bg-green-100' : 'bg-gray-100'
                                                    }`}>
                                                                                                <span className={`material-symbols-outlined ${
                                            chatbot.isActive ? 'text-green-600' : 'text-gray-400'
                                        }`}>
                                            smart_toy
                                        </span>
                                    </div>
                                                    <div className="min-w-0 w-full">
                                                        <h3 className="text-lg font-medium text-gray-900 text-base sm:text-lg truncate max-w-full flex items-center gap-2">
                                                            {chatbot.name}
                                                            <span className={`px-2 py-0.5 rounded-full text-xs ${health[chatbot.id]?.ready ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}>
                                                                {health[chatbot.id]?.ready ? 'Ready' : 'Preparing…'}
                                                            </span>
                                                        </h3>
                                                        {chatbot.description && (
                                                            <p className="text-sm text-gray-600 mb-1 break-all sm:break-words">
                                                                {chatbot.description.length > 100 
                                                                    ? chatbot.description.slice(0, 100) + '...' 
                                                                    : chatbot.description}
                                                            </p>
                                                        )}
                                                        <p className="text-sm text-gray-500 break-all">
                                                            Namespace: {chatbot.namespace}
                                                        </p>
                                                        {/* <div className="flex items-center space-x-4 mt-1">
                                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                                                                chatbot.isActive 
                                                                    ? 'bg-green-100 text-green-800' 
                                                                    : 'bg-gray-100 text-gray-800'
                                                            }`}>
                                                                {chatbot.isActive ? 'Active' : 'Inactive'}
                                                            </span>
                                                            <span className="text-xs text-gray-500">
                                                                {chatbot.files.length} files
                                                            </span>
                                                        </div> */}
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-2 w-full sm:w-auto justify-start sm:justify-end">
                                                    <button
                                                        onClick={(e) => handleDeleteChatbot(e, chatbot.id, chatbot.name)}
                                                        className="px-3 py-1 bg-red-100 text-red-800 text-xs sm:text-base rounded-md hover:bg-red-200 transition-colors"
                                                        title="Delete chatbot"
                                                    >
                                                        Delete
                                                    </button>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleSelectChatbot(chatbot);
                                                        }}
                                                        className="px-3 py-1 bg-black text-white text-xs sm:text-base rounded-md hover:bg-green-900 transition-colors"
                                                    >
                                                        Select
                                                    </button>
                                                                                        <span className={`material-symbols-outlined transform transition-transform ${
                                        expandedChatbot === chatbot.id ? 'rotate-180' : ''
                                    }`}>
                                        expand_more
                                    </span>
                                                </div>
                                            </div>
                                        </div>

                                        {/* Expanded Details */}
                                        {expandedChatbot === chatbot.id && (
                                            <div className="mt-4 p-4 bg-gray-50 rounded-lg min-w-0 overflow-hidden">
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-w-0">
                                                    {/* Left Column - Configuration */}
                                                    <div className="min-w-0">
                                                        <h4 className="text-sm font-semibold text-gray-900 mb-3">
                                                            Configuration
                                                        </h4>
                                                        <div className="space-y-3">
                                                            {chatbot.description && (
                                                                <div>
                                                                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                        Description
                                                                    </span>
                                                                    <p className="text-sm text-gray-900 mt-1 break-all sm:break-words whitespace-pre-wrap">
                                                                        {chatbot.description}
                                                                    </p>
                                                                </div>
                                                            )}
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Embedding Model
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1 break-all">
                                                                    {chatbot.embeddingType}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Chunking Process
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1 capitalize break-all">
                                                                    {chatbot.chunkingProcess.replace('-', ' ')}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Cloud Storage
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1">
                                                                    Cloud
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Namespace
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1 break-all">
                                                                    {chatbot.index}
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Right Column - Files */}
                                                    <div className="min-w-0">
                                                        <h4 className="text-sm font-semibold text-gray-900 mb-3">
                                                            Loaded Files ({chatbot.files.length})
                                                        </h4>
                                                        <div className="space-y-2 max-h-48 overflow-y-auto min-w-0">
                                                            {chatbot.files.length === 0 ? (
                                                                <p className="text-sm text-gray-500 italic">
                                                                    No files loaded
                                                                </p>
                                                            ) : (
                                                                chatbot.files.map((file) => {
                                                                    const fileIcon = getFileIcon(file.type);
                                                                    return (
                                                                        <div 
                                                                            key={file.id} 
                                                                            className="flex items-center space-x-3 p-2 bg-white rounded border min-w-0"
                                                                        >
                                                            <span className={`material-symbols-outlined ${fileIcon.color}`}>
                                                                {fileIcon.icon}
                                                            </span>
                                                                            <div className="flex-1 min-w-0">
                                                                                <p className="text-sm font-medium text-gray-900 break-all sm:truncate">
                                                                                    {file.name}
                                                                                </p>
                                                                                <p className="text-xs text-gray-500">
                                                                                    Uploaded {file.uploadedAt.toLocaleDateString()}
                                                                                </p>
                                                                            </div>
                                                                        </div>
                                                                    );
                                                                })
                                                            )}
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Timestamps */}
                                                <div className="mt-4 pt-4 border-t border-gray-200">
                                                    <div className="flex justify-between text-xs text-gray-500">
                                                        <span>
                                                            Created: {chatbot.createdAt.toLocaleString()}
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </Modal>
    );
};

export default ManageChatbotsModalComponent;
