import { Modal } from "@mui/material";
import { useState, useRef } from "react";
import ChatbotManagerStore from "../stores/ChatbotManagerStore";
import ViewStore from "../stores/ViewStore";

const CreateBotUserModalComponent = ({ open, onClose }: { open: boolean, onClose: () => void }) => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [aiProvider, setAiProvider] = useState("Gemini");
    const [errorMessage, setErrorMessage] = useState("");
    const { addError } = ViewStore();
    const { isLoading } = ChatbotManagerStore();

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
        aiProvider: string
    ) => {
        // Check if any of the fields are empty
        if (!name || !description || !aiProvider || selectedFiles.length === 0) {
            const errorMsg = "Please fill in all fields and select at least one file";
            setErrorMessage(errorMsg);
            addError(errorMsg);
            return;
        }

        const data = {
            name: name,
            description: description,
            files: files,
            aiProvider: aiProvider
        }

        const result = await ChatbotManagerStore.getState().createChatbotNormalUser(data);

        if (result) {
            onClose();
            setName("");
            setDescription("");
            setAiProvider("Gemini");
            setSelectedFiles([]);
            setErrorMessage("");
        } else {
            const errorMsg = "Failed to create normal user chatbot";
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
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[90%] sm:w-[70%] h-[90%] sm:h-[70%] glass-card rounded-lg shadow-lg p-2 sm:p-8 flex flex-col sm:flex-row gap-6 overflow-x-hidden relative">
                {/* Close button */}
                <button
                    onClick={onClose}
                    className="absolute top-2 right-2 sm:top-4 sm:right-4 z-10 glass-text opacity-60 hover:opacity-80 transition-colors p-1 rounded-full hover:glass"
                    aria-label="Close modal"
                >
                    <span className="material-symbols-outlined text-xl sm:text-2xl">close</span>
                </button>
                {/* Left side - Form fields (70%) */}
                <div className="flex flex-col gap-6 flex-1 w-full sm:w-[70%] min-w-0 overflow-y-auto">
                    <h1 className="text-base sm:text-2xl font-semibold glass-text text-center">Create New Chatbot</h1>

                    <div className="flex flex-col gap-4 flex-1 min-w-0">
                        {/* Chatbot Name */}
                        <div className="flex flex-col gap-2">
                            <label className="text-xs sm:text-sm font-medium glass-text">Chatbot Name</label>
                            <input
                                type="text"
                                placeholder="Enter chatbot name"
                                className="w-full p-2 sm:p-3 glass-input text-xs sm:text-sm glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-300"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>

                        {/* Description */}
                        <div className="flex flex-col gap-2 min-w-0">
                            <label className="text-xs sm:text-sm font-medium glass-text">Description</label>
                            <input
                                type="text"
                                placeholder="Enter chatbot description"
                                className="w-full p-2 sm:p-3 glass-input text-xs sm:text-sm glass-text rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-300"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        {/* AI Provider selection */}
                        <div className="flex flex-col gap-2 min-w-0">
                            <label className="text-xs sm:text-sm font-medium glass-text">AI Provider</label>
                            <div className="flex flex-wrap gap-4">
                                <div className="flex items-center">
                                    <input
                                        type="radio"
                                        id="Gemini"
                                        name="aiProvider"
                                        value="Gemini"
                                        className="mr-2"
                                        defaultChecked
                                        onChange={(e) => setAiProvider(e.target.value)}
                                    />
                                    <label htmlFor="Gemini" className="text-xs sm:text-sm glass-text cursor-pointer">Gemini</label>
                                </div>
                                <div className="flex items-center">
                                    <input
                                        type="radio"
                                        id="OpenAI"
                                        name="aiProvider"
                                        value="OpenAI"
                                        className="mr-2"
                                        onChange={(e) => setAiProvider(e.target.value)}
                                    />
                                    <label htmlFor="OpenAI" className="text-xs sm:text-sm glass-text cursor-pointer">OpenAI</label>
                                </div>
                            </div>
                        </div>

                        {/* Files upload (only PDFs, DOCS, CSVs and TXT) */}
                        <div className="flex flex-col gap-2 min-w-0">
                            <label className="text-xs sm:text-sm font-medium glass-text">Files</label>
                            <div className="relative">
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    multiple
                                    onChange={handleFileChange}
                                    accept=".pdf,.doc,.docx,.csv,.txt"
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div className="w-full p-2 sm:p-3 glass-input text-xs sm:text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent cursor-pointer flex items-center gap-2">
                                    <span className="material-symbols-outlined glass-text opacity-70">upload_file</span>
                                    <span className="glass-text text-xs sm:text-base truncate">Choose files (PDF, DOC, CSV, TXT)</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Error message */}
                    {errorMessage && (
                        <div className="text-red-300 text-xs sm:text-sm text-center p-3 glass rounded-md border border-red-300">
                            {errorMessage}
                        </div>
                    )}

                    <div className="flex justify-center">
                        <button
                            className="w-full sm:w-auto text-xs sm:text-sm px-8 py-3 glass-button glass-text rounded-md hover:glass-light transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            onClick={() => handleSubmit(name, description, selectedFiles, aiProvider)}
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
                <div className="w-full sm:w-[30%] h-[40%] sm:h-full flex flex-col gap-2 sm:gap-4 min-w-0 rounded-lg shadow-lg p-2 sm:p-8">
                    <h2 className="text-base sm:text-lg font-medium glass-text text-center">Selected Files</h2>
                    <div className="flex-1 border border-gray-200 rounded-md p-4 glass overflow-y-auto min-w-0">
                        <div className="flex flex-col gap-3">
                            {selectedFiles.length > 0 ? (
                                selectedFiles.map((file, index) => {
                                    const { icon, color } = getFileIcon(file.name);
                                    const fileType = file.name.split('.').pop()?.toUpperCase() || 'FILE';

                                    return (
                                        <div key={index} className="flex items-center gap-3 p-1 sm:p-3 glass rounded-md shadow-sm min-w-0">
                                            <div className="flex-shrink-0">
                                                <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-xs sm:text-sm font-medium glass-text break-all sm:truncate" title={file.name}>
                                                    {file.name}
                                                </p>
                                                <p className="text-xs glass-text opacity-70">{fileType}</p>
                                            </div>
                                            <button
                                                onClick={() => removeFile(index)}
                                                className="flex-shrink-0 glass-text opacity-60 hover:text-red-500 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-xs sm:text-sm">close</span>
                                            </button>
                                        </div>
                                    );
                                })
                            ) : (
                                /* Empty state when no files */
                                <div className="text-center py-8 glass-text opacity-60">
                                    <span className="material-symbols-outlined text-2xl sm:text-4xl mb-2 block">upload_file</span>
                                    <p className="text-xs sm:text-sm">No files selected</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </Modal>
    )
}

export default CreateBotUserModalComponent;