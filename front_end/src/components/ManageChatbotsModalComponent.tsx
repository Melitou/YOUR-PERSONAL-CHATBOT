import { Modal } from "@mui/material";
import { useState, useEffect } from "react";

import ChatbotManagerStore, { type CreatedChatbot, type ChatbotFile } from "../stores/ChatbotManagerStore";

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
        addChatbot, 
        isLoading, 
        error, 
        toggleChatbotStatus 
    } = ChatbotManagerStore();
    const [expandedChatbot, setExpandedChatbot] = useState<string | null>(null);


    // Add fake chatbots for testing/development when component mounts
    useEffect(() => {
        if (chatbots.length === 0) {
            // Create fake files
            const fakeFiles1: ChatbotFile[] = [
                {
                    id: "file1",
                    name: "product_manual.pdf",
                    size: 2048576, // 2MB
                    type: "application/pdf",
                    uploadedAt: new Date("2024-01-15")
                },
                {
                    id: "file2",
                    name: "company_policies.docx",
                    size: 1024000, // 1MB
                    type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    uploadedAt: new Date("2024-01-16")
                }
            ];

            const fakeFiles2: ChatbotFile[] = [
                {
                    id: "file3",
                    name: "customer_data.csv",
                    size: 512000, // 512KB
                    type: "text/csv",
                    uploadedAt: new Date("2024-01-20")
                },
                {
                    id: "file4",
                    name: "support_guide.txt",
                    size: 256000, // 256KB
                    type: "text/plain",
                    uploadedAt: new Date("2024-01-21")
                }
            ];

            const fakeFiles3: ChatbotFile[] = [
                {
                    id: "file5",
                    name: "technical_specs.pdf",
                    size: 3072000, // 3MB
                    type: "application/pdf",
                    uploadedAt: new Date("2024-01-25")
                }
            ];

            const fakeFiles4: ChatbotFile[] = [
                {
                    id: "file6",
                    name: "api_documentation.md",
                    size: 512000, // 512KB
                    type: "text/markdown",
                    uploadedAt: new Date("2024-02-01")
                },
                {
                    id: "file7",
                    name: "user_guide.pdf",
                    size: 1536000, // 1.5MB
                    type: "application/pdf",
                    uploadedAt: new Date("2024-02-02")
                }
            ];

            const fakeFiles5: ChatbotFile[] = [
                {
                    id: "file8",
                    name: "faq_database.txt",
                    size: 256000, // 256KB
                    type: "text/plain",
                    uploadedAt: new Date("2024-02-10")
                }
            ];

            // Add fake chatbots for demo/development purposes
            const fakeChatbots = [
                {
                    name: "Customer Support Bot",
                    description: "Handles customer inquiries and support requests",
                    namespace: "customer_support",
                    index: "support_index_v1",
                    embeddingType: "text-embedding-3-small" as const,
                    chunkingProcess: "recursive" as const,
                    files: fakeFiles1,
                    isActive: true
                },
                {
                    name: "Product Assistant",
                    description: "Provides product information and recommendations",
                    namespace: "product_help",
                    index: "product_index_v2",
                    embeddingType: "text-embedding-3-large" as const,
                    chunkingProcess: "semantic" as const,
                    files: fakeFiles2,
                    isActive: true
                },
                {
                    name: "Technical Documentation Bot",
                    description: "Answers technical questions from documentation",
                    namespace: "tech_docs",
                    index: "tech_index_v1",
                    embeddingType: "gemini-embedding-001" as const,
                    chunkingProcess: "fixed-size" as const,
                    files: fakeFiles3,
                    isActive: false
                },
                {
                    name: "API Helper",
                    description: "Assists developers with API usage and integration",
                    namespace: "api_support",
                    index: "api_index_v1",
                    embeddingType: "text-embedding-3-small" as const,
                    chunkingProcess: "recursive" as const,
                    files: fakeFiles4,
                    isActive: true
                },
                {
                    name: "FAQ Bot",
                    description: "Answers frequently asked questions",
                    namespace: "faq_assistant",
                    index: "faq_index_v1",
                    embeddingType: "text-embedding-3-large" as const,
                    chunkingProcess: "semantic" as const,
                    files: fakeFiles5,
                    isActive: false
                }
            ];

            fakeChatbots.forEach(bot => addChatbot(bot));
        }
    }, [chatbots.length, addChatbot]);

    const formatFileSize = (bytes: number): string => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

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

    const getRandomConversationCount = () => {
        // Generate random conversation count for demo purposes
        return Math.floor(Math.random() * 150) + 1;
    };

    const toggleExpanded = (chatbotId: string) => {
        setExpandedChatbot(expandedChatbot === chatbotId ? null : chatbotId);
    };

    const handleSelectChatbot = (chatbot: CreatedChatbot) => {
        if (onSelectChatbot) {
            onSelectChatbot(chatbot);
        }
        onClose();
    };

    const handleToggleStatus = (e: React.MouseEvent, chatbotId: string) => {
        e.stopPropagation();
        toggleChatbotStatus(chatbotId);
    };

    const handleDeleteChatbot = (e: React.MouseEvent, chatbotId: string, chatbotName: string) => {
        e.stopPropagation();
        
        if (window.confirm(`Are you sure you want to delete "${chatbotName}"? This action cannot be undone.`)) {
            // In demo mode, just remove from local state
            const { deleteChatbot } = ChatbotManagerStore.getState();
            deleteChatbot(chatbotId);
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
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[70%] h-[70%] bg-white rounded-lg shadow-lg p-8 flex flex-row gap-6">
                <div className="flex flex-col gap-6 flex-1 w-[70%]">
                    {/* Header */}
                    <div className="border-b border-gray-200 px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                                <h2 className="text-xl font-semibold text-gray-900">
                                    My Chatbots ({chatbots.length})
                                </h2>
                                <span className="text-sm text-gray-500">
                                    Demo Mode
                                </span>
                            </div>
                            <button
                                onClick={onClose}
                                className="text-gray-400 hover:text-gray-600 transition-colors"
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
                                <p className="text-gray-500 text-center">Loading chatbots...</p>
                            </div>
                        ) : 
                        /* Error State */
                        error ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6">
                                <span className="material-symbols-outlined text-6xl text-red-300 mb-4 text-center">
                                    error
                                </span>
                                <h3 className="text-lg font-medium text-gray-900 mb-2">
                                    Error in demo mode
                                </h3>
                                <p className="text-gray-500 text-center mb-4">
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
                                <h3 className="text-lg font-medium text-gray-900 mb-2">
                                    No chatbots yet
                                </h3>
                                <p className="text-gray-500 text-center">
                                    Create your first chatbot to get started with AI assistance.
                                </p>
                            </div>
                        ) : (
                            <div className="divide-y divide-gray-200">
                                {chatbots.map((chatbot) => (
                                    <div key={chatbot.id} className="p-6">
                                        {/* Chatbot List Item */}
                                        <div 
                                            className="cursor-pointer hover:bg-gray-50 p-4 rounded-lg transition-colors"
                                            onClick={() => toggleExpanded(chatbot.id)}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex items-center space-x-4">
                                                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
                                                        chatbot.isActive ? 'bg-green-100' : 'bg-gray-100'
                                                    }`}>
                                                                                                <span className={`material-symbols-outlined ${
                                            chatbot.isActive ? 'text-green-600' : 'text-gray-400'
                                        }`}>
                                            smart_toy
                                        </span>
                                                    </div>
                                                    <div>
                                                        <h3 className="text-lg font-medium text-gray-900">
                                                            {chatbot.name}
                                                        </h3>
                                                        {chatbot.description && (
                                                            <p className="text-sm text-gray-600 mb-1">
                                                                {chatbot.description}
                                                            </p>
                                                        )}
                                                        <p className="text-sm text-gray-500">
                                                            Namespace: {chatbot.namespace}
                                                        </p>
                                                        <div className="flex items-center space-x-4 mt-1">
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
                                                            <span className="text-xs text-gray-500">
                                                                {getRandomConversationCount()} conversations
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div className="flex items-center space-x-2">
                                                    <button
                                                        onClick={(e) => handleToggleStatus(e, chatbot.id)}
                                                        className={`px-3 py-1 text-xs rounded-md transition-colors ${
                                                            chatbot.isActive 
                                                                ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200' 
                                                                : 'bg-green-100 text-green-800 hover:bg-green-200'
                                                        }`}
                                                        title={chatbot.isActive ? 'Deactivate' : 'Activate'}
                                                    >
                                                        {chatbot.isActive ? 'Deactivate' : 'Activate'}
                                                    </button>
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
                                            <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                    {/* Left Column - Configuration */}
                                                    <div>
                                                        <h4 className="text-sm font-semibold text-gray-900 mb-3">
                                                            Configuration
                                                        </h4>
                                                        <div className="space-y-3">
                                                            {chatbot.description && (
                                                                <div>
                                                                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                        Description
                                                                    </span>
                                                                    <p className="text-sm text-gray-900 mt-1">
                                                                        {chatbot.description}
                                                                    </p>
                                                                </div>
                                                            )}
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Embedding Model
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1">
                                                                    {chatbot.embeddingType}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Chunking Process
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1 capitalize">
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
                                                                    Index
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1">
                                                                    {chatbot.index}
                                                                </p>
                                                            </div>
                                                            <div>
                                                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                                                                    Conversations
                                                                </span>
                                                                <p className="text-sm text-gray-900 mt-1">
                                                                    {getRandomConversationCount()} total conversations
                                                                </p>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Right Column - Files */}
                                                    <div>
                                                        <h4 className="text-sm font-semibold text-gray-900 mb-3">
                                                            Loaded Files ({chatbot.files.length})
                                                        </h4>
                                                        <div className="space-y-2 max-h-48 overflow-y-auto">
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
                                                                            className="flex items-center space-x-3 p-2 bg-white rounded border"
                                                                        >
                                                                                                                                        <span className={`material-symbols-outlined ${fileIcon.color}`}>
                                                                {fileIcon.icon}
                                                            </span>
                                                                            <div className="flex-1 min-w-0">
                                                                                <p className="text-sm font-medium text-gray-900 truncate">
                                                                                    {file.name}
                                                                                </p>
                                                                                <p className="text-xs text-gray-500">
                                                                                    {formatFileSize(file.size)} • Uploaded {file.uploadedAt.toLocaleDateString()}
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
                                                        <span>
                                                            Last updated: {chatbot.updatedAt.toLocaleString()}
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
