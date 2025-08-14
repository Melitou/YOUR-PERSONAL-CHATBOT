import { Modal } from "@mui/material";
import { useState, useRef, useEffect } from "react";
import ChatbotManagerStore from "../stores/ChatbotManagerStore";
import ViewStore from "../stores/ViewStore";

const CreateBotSuperUserModalComponent = ({
    open,
    onClose,

}: {
    open: boolean,
    onClose: () => void,
}) => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [chunkingMethod, setChunkingMethod] = useState("Fixed Token");
    const [embeddingModel, setEmbeddingModel] = useState("text-embedding-3-small");
    const [errorMessage, setErrorMessage] = useState("");
    const { addError } = ViewStore();

    const { isLoading } = ChatbotManagerStore((state: any) => state);

    useEffect(() => {
        if (open) {
            setName("");
            setDescription("");
            setSelectedFiles([]);
            setChunkingMethod("Fixed Token");
            setEmbeddingModel("text-embedding-3-small");
            setErrorMessage("");

            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    }, [open]);

    const chunkingOptions = [
        "Fixed Token",
        "Semantic",
        "Fixed-Line",
        "Recursive"
    ];

    const embeddingOptions = [
        "text-embedding-3-small",
        "text-embedding-3-large",
        "text-embedding-ada-002",
        // "text-embedding-005",
        // "text-multilingual-embedding-002",
        // "multilingual-e5-large",
        "gemini-embedding-001"
    ];

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        try {
            const files = Array.from(event.target.files || []);
            // Filter for allowed file types  
            const allowedTypes = ['.pdf', '.doc', '.docx', '.csv', '.txt'];
            const validFiles = files.filter(file => {
                const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
                return allowedTypes.includes(fileExtension);
            });

            const invalidFiles = files.filter(file => {
                const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
                return !allowedTypes.includes(fileExtension);
            });

            if (invalidFiles.length > 0) {
                const errorMsg = `Invalid file types: ${invalidFiles.map(f => f.name).join(', ')}. Only PDF, DOC, DOCX, CSV, and TXT files are allowed.`;
                addError(errorMsg);
                console.error('Invalid file types uploaded:', invalidFiles.map(f => f.name));
            }

            setSelectedFiles(prev => [...prev, ...validFiles]);
        } catch (error) {
            const errorMsg = 'Error processing uploaded files';
            console.error('File upload error:', error);
            addError(errorMsg);
        }
    };

    const removeFile = (index: number) => {
        setSelectedFiles(prev => prev.filter((_, i) => i !== index));
        // Clear the file input to reflect the change
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    const getFileIcon = (fileName: string) => {
        const extension = fileName.split('.').pop()?.toLowerCase();
        switch (extension) {
            case 'pdf':
                return { icon: 'picture_as_pdf', color: 'text-red-500' };
            case 'doc':
            case 'docx':
                return { icon: 'description', color: 'text-blue-500' };
            case 'csv':
                return { icon: 'table_chart', color: 'text-green-500' };
            case 'txt':
                return { icon: 'description', color: 'text-gray-500' };
            default:
                return { icon: 'insert_drive_file', color: 'text-gray-400' };
        }
    };

    const handleSubmit = async (
        name: string,
        description: string,
        files: File[],
        chunkingMethod: string,
        embeddingModel: string
    ) => {
        try {
            console.log('Creating chatbot with name:', name, 'description:', description, 'files:', files, 'chunkingMethod:', chunkingMethod, 'embeddingModel:', embeddingModel);

            if (!name || !description || !files.length || !chunkingMethod || !embeddingModel) {
                const errorMsg = "Please fill in all fields and select at least one file";
                setErrorMessage(errorMsg);
                addError(errorMsg);
                return;
            }

            const data = {
                name: name,
                description: description,
                files: files,
                chunkingMethod: chunkingMethod,
                embeddingModel: embeddingModel
            }

            const result = await ChatbotManagerStore.getState().createChatbotSuperUser(data);

            if (result) {
                onClose();
                setName("");
                setDescription("");
                setSelectedFiles([]);
                setChunkingMethod("Fixed Token");
                setEmbeddingModel("text-embedding-3-small");
                setErrorMessage("");
            } else {
                const errorMsg = "Failed to create super user chatbot";
                setErrorMessage(errorMsg);
                addError(errorMsg);
            }
        } catch (error) {
            const errorMsg = error instanceof Error ? error.message : 'Failed to create super user chatbot. Please try again.';
            console.error('Failed to create super user chatbot:', errorMsg);
            setErrorMessage(errorMsg);
            addError(errorMsg);
        }
    }

    return (
        <Modal
            open={open}
            onClose={onClose}
            sx={{
                backdropFilter: 'blur(5px)',
                backgroundColor: 'rgba(0, 0, 0, 0.5)'
            }}
        >
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] glass-card shadow-lg p-8 flex flex-row gap-6">
                {/* Left side - Form fields (70%) */}
                <div className="flex flex-col gap-6 flex-1 w-[70%]">
                    <h1 className="text-2xl font-semibold glass-text text-center">Create New Agent</h1>

                    <div className="flex flex-col gap-4 flex-1 overflow-y-auto">
                        {/* Agent Name (Namespace) */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium glass-text">
                                Agent Name <span className="text-xs glass-text opacity-70">(This is the Namespace)</span>
                            </label>
                            <input
                                type="text"
                                placeholder="Enter agent name"
                                className="w-full p-3 glass-input glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-300"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>

                        {/* Description */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium glass-text">Agent Description</label>
                            <textarea
                                placeholder="Enter agent description"
                                className="w-full p-3 glass-input glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent h-24 resize-none placeholder-gray-300"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        {/* Files upload */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium glass-text">Upload Files</label>
                            <div className="relative">
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    onChange={handleFileChange}
                                    accept=".pdf,.doc,.docx,.csv,.txt"
                                    className="sr-only"
                                    id="file-upload"
                                />
                                <label
                                    htmlFor="file-upload"
                                    className="w-full p-3 glass-input rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer flex items-center gap-2 hover:glass-light transition-colors"
                                >
                                    <span className="material-symbols-outlined glass-text opacity-70">upload_file</span>
                                    <span className="glass-text">Choose files (PDF, DOC, CSV, TXT)</span>
                                </label>
                            </div>
                        </div>

                        {/* Chunking Method Dropdown */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium glass-text">Chunking Method</label>
                            <select
                                className="w-full p-3 glass-input glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                value={chunkingMethod}
                                onChange={(e) => setChunkingMethod(e.target.value)}
                            >
                                {chunkingOptions.map((option) => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>

                        {/* Embedding Model Dropdown */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium glass-text">Embedding Model</label>
                            <select
                                className="w-full p-3 glass-input glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                value={embeddingModel}
                                onChange={(e) => setEmbeddingModel(e.target.value)}
                            >
                                {embeddingOptions.map((option) => (
                                    <option key={option} value={option}>{option}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Error message */}
                    {errorMessage && (
                        <div className="text-red-300 text-sm text-center p-3 glass rounded-md border border-red-300">
                            {errorMessage}
                        </div>
                    )}

                    <div className="flex justify-center">
                        <button
                            className="px-8 py-3 glass-button glass-text rounded-md hover:glass-light transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                            onClick={() => handleSubmit(name, description, selectedFiles, chunkingMethod, embeddingModel)}
                            disabled={isLoading}
                        >
                            {isLoading && (
                                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                            )}
                            {isLoading ? "Creating..." : "Create Agent"}
                        </button>
                    </div>
                </div>

                {/* Right side - Files preview (30%) */}
                <div className="w-[30%] flex flex-col gap-4">
                    <h2 className="text-lg font-medium glass-text text-center">Selected Files</h2>
                    <div className="flex-1 border border-gray-200 rounded-md p-4 glass overflow-y-auto">
                        <div className="flex flex-col gap-3">
                            {selectedFiles.length > 0 ? (
                                selectedFiles.map((file, index) => {
                                    const { icon, color } = getFileIcon(file.name);
                                    const fileType = file.name.split('.').pop()?.toUpperCase() || 'FILE';

                                    return (
                                        <div key={index} className="flex items-center gap-3 p-3 glass rounded-md shadow-sm">
                                            <div className="flex-shrink-0">
                                                <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium glass-text truncate" title={file.name}>
                                                    {file.name}
                                                </p>
                                                <p className="text-xs glass-text opacity-70">{fileType}</p>
                                            </div>
                                            <button
                                                onClick={() => removeFile(index)}
                                                className="flex-shrink-0 glass-text opacity-60 hover:text-red-500 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-sm">close</span>
                                            </button>
                                        </div>
                                    );
                                })
                            ) : (
                                /* Empty state when no files */
                                <div className="text-center py-8 glass-text opacity-60">
                                    <span className="material-symbols-outlined text-4xl mb-2 block">upload_file</span>
                                    <p className="text-sm">No files selected</p>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Configuration Summary */}
                    <div className="border border-gray-200 rounded-md p-4 glass">
                        <h3 className="text-sm font-medium glass-text mb-2">Configuration</h3>
                        <div className="text-xs glass-text opacity-80 space-y-1">
                            <div><span className="font-medium">Chunking:</span> {chunkingMethod}</div>
                            <div><span className="font-medium">Embedding:</span> {embeddingModel}</div>
                            <div><span className="font-medium">Storage:</span> Cloud (Auto)</div>
                        </div>
                    </div>
                </div>
            </div>
        </Modal>
    )
}

export default CreateBotSuperUserModalComponent;