import { Modal } from "@mui/material";
import { useState, useEffect } from "react";
import React from "react";
// import { chatbotApi } from "../utils/api";
import ChatbotManagerStore, { type CreatedChatbot } from "../stores/ChatbotManagerStore";
import LoadedChatbotStore from "../stores/LoadedChatbotStore";
import ViewStore from "../stores/ViewStore";
import AssignClientsModalComponent from "./AssignClientsModalComponent";
import UserAuthStore from "../stores/UserAuthStore";

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
    const [assignClientsModalOpen, setAssignClientsModalOpen] = useState(false);
    const [selectedChatbotForAssignment, setSelectedChatbotForAssignment] = useState<CreatedChatbot | null>(null);
    const { setLoadedChatbot } = LoadedChatbotStore((state: any) => state);
    // const [health, setHealth] = useState<Record<string, { ready: boolean; vectors: number }>>({});
    const { addError } = ViewStore();
    const { user } = UserAuthStore();

    // Fetch real chatbots when modal opens
    useEffect(() => {
        if (open) {
            fetchChatbots().catch((error) => {
                const errorMsg = 'Failed to load chatbots';
                console.error('Failed to load chatbots:', error);
                addError(errorMsg);
            });
        }
    }, [open, fetchChatbots, addError]);

    // Fetch health for expanded chatbot
    // useEffect(() => {
    //     const id = expandedChatbot;
    //     if (!id) return;
    //     let cancelled = false;
    //     const fetchHealth = async () => {
    //         try {
    //             const res = await chatbotApi.getChatbotHealth(id);
    //             if (!cancelled) {
    //                 setHealth((h) => ({ ...h, [id]: { ready: Boolean(res.ready), vectors: Number(res.pinecone_vectors || 0) } }));
    //             }
    //         } catch {
    //             // ignore; badge will stay unknown
    //         }
    //     };
    //     fetchHealth();
    //     const t = setInterval(fetchHealth, 3000);
    //     return () => { cancelled = true; clearInterval(t); };
    // }, [expandedChatbot]);

    // Also fetch health for all chatbots when list loads, so pills don't stay in "Preparing…"
    // useEffect(() => {
    //     if (!open || !chatbots || chatbots.length === 0) return;
    //     let cancelled = false;
    //     const loadAll = async () => {
    //         try {
    //             const entries = await Promise.all(chatbots.map(async (c) => {
    //                 try {
    //                     const res = await chatbotApi.getChatbotHealth(c.id);
    //                     return [c.id, { ready: Boolean(res.ready), vectors: Number(res.pinecone_vectors || 0) }] as const;
    //                 } catch {
    //                     return [c.id, { ready: false, vectors: 0 }] as const;
    //                 }
    //             }));
    //             if (!cancelled) {
    //                 setHealth(Object.fromEntries(entries));
    //             }
    //         } catch {/* ignore */ }
    //     };
    //     loadAll();
    //     const t = setInterval(loadAll, 10000);
    //     return () => { cancelled = true; clearInterval(t); };
    // }, [open, chatbots]);

    const getFileIcon = (type: string) => {
        if (type.includes('pdf')) return { icon: 'picture_as_pdf', color: 'text-red-500' };
        if (type.includes('word') || type.includes('document')) return { icon: 'description', color: 'text-blue-500' };
        if (type.includes('csv')) return { icon: 'table_chart', color: 'text-green-500' };
        if (type.includes('markdown')) return { icon: 'code', color: 'text-purple-500' };
        if (type.includes('text')) return { icon: 'description', color: 'glass-text opacity-70' };
        if (type.includes('image')) return { icon: 'image', color: 'text-yellow-500' };
        if (type.includes('excel') || type.includes('spreadsheet')) return { icon: 'table_chart', color: 'text-green-600' };
        return { icon: 'insert_drive_file', color: 'text-gray-400' };
    };

    const toggleExpanded = (chatbotId: string) => {
        setExpandedChatbot(expandedChatbot === chatbotId ? null : chatbotId);
    };



    const getFileCountSummary = (files: any[]): string => {
        const count = files.length;
        if (count === 0) return 'No files';
        if (count === 1) return '1 file';
        return `${count} files`;
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
        <>
            <Modal
                open={open}
                onClose={onClose}
                disableEnforceFocus={assignClientsModalOpen}
                disableAutoFocus={assignClientsModalOpen}
                sx={{
                    backdropFilter: 'blur(5px)',
                    backgroundColor: 'rgba(0, 0, 0, 0.5)'
                }}
            >
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[70%] h-[70%] glass-card shadow-lg p-8 flex flex-row gap-6">
                    <div className="flex flex-col gap-6 flex-1 w-[70%]">
                        {/* Header */}
                        <div className="border-b border-gray-200 px-6 py-4">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-4">
                                    <h2 className="text-xl font-semibold glass-text">
                                        My Chatbots ({chatbots.length})
                                    </h2>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="glass-text opacity-60 hover:opacity-80 transition-colors"
                                >
                                    <span className="material-symbols-outlined">close</span>
                                </button>
                            </div>
                        </div>

                        {/* Content */}
                        <div className="overflow-y-auto max-h-[calc(80vh-120px)]">
                            {/* Loading State */}
                            {isLoading ? (
                                <div className="flex flex-col items-center justify-center py-12 px-6">
                                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                                    <p className="glass-text opacity-70 text-center">Loading chatbots...</p>
                                </div>
                            ) :
                                /* Error State */
                                error ? (
                                    <div className="flex flex-col items-center justify-center py-12 px-6">
                                        <span className="material-symbols-outlined text-6xl text-red-300 mb-4 text-center">
                                            error
                                        </span>
                                        <h3 className="text-lg font-medium glass-text mb-2">
                                            Error loading chatbots
                                        </h3>
                                        <p className="glass-text opacity-70 text-center mb-4">
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
                                            <h3 className="text-lg font-medium glass-text mb-2">
                                                No chatbots yet
                                            </h3>
                                            <p className="glass-text opacity-70 text-center">
                                                Create your first chatbot to get started with AI assistance.
                                            </p>
                                        </div>
                                    ) : (
                                        <div className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
                                            {chatbots.map((chatbot) => (
                                                <div key={chatbot.id} className="p-6">
                                                    {/* Chatbot List Item */}
                                                    <div
                                                        className="cursor-pointer hover:glass p-4 rounded-lg transition-colors"
                                                        onClick={() => toggleExpanded(chatbot.id)}
                                                    >
                                                        <div className="flex items-center justify-between">
                                                            <div className="flex items-center space-x-4">
                                                                <div className={`w-12 h-12 rounded-full flex items-center justify-center ${chatbot.isActive ? 'bg-green-100' : 'bg-gray-100'
                                                                    }`}>
                                                                    <span className={`material-symbols-outlined ${chatbot.isActive ? 'text-green-600' : 'text-gray-400'
                                                                        }`}>
                                                                        smart_toy
                                                                    </span>
                                                                </div>
                                                                <div>
                                                                    <h3 className="text-lg font-medium glass-text">
                                                                        {chatbot.name}
                                                                        {/* <span className={`px-2 py-0.5 rounded-full text-xs ${health[chatbot.id]?.ready ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}>
                                                                        {health[chatbot.id]?.ready ? 'Ready' : 'Preparing…'}
                                                                    </span> */}
                                                                    </h3>
                                                                    {chatbot.description && (
                                                                        <p className="text-sm glass-text opacity-80 mb-1">
                                                                            {chatbot.description.length > 100
                                                                                ? chatbot.description.slice(0, 100) + '...'
                                                                                : chatbot.description}
                                                                        </p>
                                                                    )}
                                                                    <p className="text-sm glass-text opacity-70">
                                                                        Namespace: {chatbot.namespace}
                                                                    </p>
                                                                    <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-2">
                                                                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${chatbot.isActive
                                                                            ? 'bg-green-100 text-green-800'
                                                                            : 'bg-gray-100 text-gray-800'
                                                                            }`}>
                                                                            {chatbot.isActive ? 'Active' : 'Inactive'}
                                                                        </span>
                                                                        <span className="text-xs glass-text opacity-70">
                                                                            {getFileCountSummary(chatbot.files)}
                                                                        </span>
                                                                    </div>

                                                                </div>
                                                            </div>
                                                            <div className="flex items-center space-x-2">
                                                                {(user?.role === 'User' || user?.role === 'Super User') && (
                                                                    <button
                                                                        onClick={(e) => {
                                                                            e.stopPropagation();
                                                                            setSelectedChatbotForAssignment(chatbot);
                                                                            setAssignClientsModalOpen(true);
                                                                        }}
                                                                        className="px-3 py-1 bg-green-100 text-green-800 text-xs rounded-md hover:bg-green-200 transition-colors"
                                                                        title="Assign to clients"
                                                                    >
                                                                        Assign Clients
                                                                    </button>
                                                                )}
                                                                <button
                                                                    onClick={(e) => handleDeleteChatbot(e, chatbot.id, chatbot.name)}
                                                                    className="px-3 py-1 bg-red-100 text-red-800 text-xs rounded-md hover:bg-red-200 transition-colors"
                                                                    title="Delete chatbot"
                                                                >
                                                                    Delete
                                                                </button>
                                                                <button
                                                                    onClick={(e) => {
                                                                        e.stopPropagation();
                                                                        handleSelectChatbot(chatbot);
                                                                    }}
                                                                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                                                                >
                                                                    Select
                                                                </button>
                                                                <span className={`material-symbols-outlined transform transition-transform ${expandedChatbot === chatbot.id ? 'rotate-180' : ''
                                                                    }`}>
                                                                    expand_more
                                                                </span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Expanded Details */}
                                                    {expandedChatbot === chatbot.id && (
                                                        <div className="mt-4 p-4 glass rounded-lg">
                                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                                {/* Left Column - Configuration */}
                                                                <div>
                                                                    <h4 className="text-sm font-semibold glass-text mb-3">
                                                                        Configuration
                                                                    </h4>
                                                                    <div className="space-y-3">
                                                                        {chatbot.description && (
                                                                            <div>
                                                                                <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                                    Description
                                                                                </span>
                                                                                <p className="text-sm glass-text mt-1">
                                                                                    {chatbot.description}
                                                                                </p>
                                                                            </div>
                                                                        )}
                                                                        <div>
                                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                                Embedding Model
                                                                            </span>
                                                                            <p className="text-sm glass-text mt-1">
                                                                                {chatbot.embeddingType}
                                                                            </p>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                                Chunking Process
                                                                            </span>
                                                                            <p className="text-sm glass-text mt-1 capitalize">
                                                                                {chatbot.chunkingProcess.replace('-', ' ')}
                                                                            </p>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                                Cloud Storage
                                                                            </span>
                                                                            <p className="text-sm glass-text mt-1">
                                                                                Cloud
                                                                            </p>
                                                                        </div>
                                                                        <div>
                                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                                Namespace
                                                                            </span>
                                                                            <p className="text-sm glass-text mt-1">
                                                                                {chatbot.index}
                                                                            </p>
                                                                        </div>
                                                                    </div>
                                                                </div>

                                                                {/* Right Column - Files */}
                                                                <div>
                                                                    <h4 className="text-sm font-semibold glass-text mb-3">
                                                                        Loaded Files ({chatbot.files.length})
                                                                    </h4>
                                                                    <div className="space-y-2 max-h-48 overflow-y-auto">
                                                                        {chatbot.files.length === 0 ? (
                                                                            <p className="text-sm glass-text opacity-70 italic">
                                                                                No files loaded
                                                                            </p>
                                                                        ) : (
                                                                            chatbot.files.map((file) => {
                                                                                const fileIcon = getFileIcon(file.type);
                                                                                return (
                                                                                    <div
                                                                                        key={file.id}
                                                                                        className="flex items-center space-x-3 p-2 rounded border"
                                                                                    >
                                                                                        <span className={`material-symbols-outlined ${fileIcon.color}`}>
                                                                                            {fileIcon.icon}
                                                                                        </span>
                                                                                        <div className="flex-1 min-w-0">
                                                                                            <p className="text-sm font-medium glass-text truncate">
                                                                                                {file.name}
                                                                                            </p>
                                                                                            <p className="text-xs glass-text opacity-70">
                                                                                                Uploaded {file.uploadedAt.toLocaleDateString()}
                                                                                            </p>
                                                                                        </div>
                                                                                    </div>
                                                                                );
                                                                            })
                                                                        )}
                                                                    </div>
                                                                    <div className="mt-4">
                                                                        <button className="w-full px-4 py-2 bg-[#88b999] text-white text-sm rounded-md hover:bg-[#33b849] transition-colors flex items-center justify-center space-x-2 hover:cursor-pointer">
                                                                            <span className="material-symbols-outlined">auto_fix_high</span>
                                                                            <span>Enhance Chatbot</span>
                                                                        </button>
                                                                    </div>
                                                                </div>
                                                            </div>

                                                            {/* Timestamps */}
                                                            <div className="mt-4 pt-4 border-t border-gray-200">
                                                                <div className="flex justify-between text-xs glass-text opacity-70">
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

            {/* Assign clients modal */}
            {
                selectedChatbotForAssignment && (
                    <AssignClientsModalComponent
                        open={assignClientsModalOpen}
                        onClose={() => {
                            setAssignClientsModalOpen(false);
                            setSelectedChatbotForAssignment(null);
                        }}
                        chatbotId={selectedChatbotForAssignment.id}
                        chatbotName={selectedChatbotForAssignment.name}
                    />
                )
            }
        </>
    );
};

export default ManageChatbotsModalComponent;
