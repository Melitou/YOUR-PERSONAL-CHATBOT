import { Modal } from "@mui/material";
import { useState, useRef } from "react";

const CreateBotUserModalComponent = ({ open, onClose, onSubmit }: { open: boolean, onClose: () => void, onSubmit: (name: string, description: string, aiProvider: string, selectedFiles: File[]) => void }) => {
    const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [aiProvider, setAiProvider] = useState("gemini");
    const [errorMessage, setErrorMessage] = useState("");

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const files = Array.from(event.target.files || []);
        // Filter for allowed file types
        const allowedTypes = ['.pdf', '.doc', '.docx', '.csv', '.txt'];
        const validFiles = files.filter(file => {
            const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
            return allowedTypes.includes(fileExtension);
        });
        setSelectedFiles(prev => [...prev, ...validFiles]);
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

    const handleSubmit = () => {
        console.log("Name: ", name);
        console.log("Description: ", description);
        console.log("AI Provider: ", aiProvider);
        console.log("Selected Files: ", selectedFiles);

        // Check if any of the fields are empty
        if (!name || !description || !aiProvider || selectedFiles.length === 0) {
            setErrorMessage("Please fill in all fields and select at least one file");
            return;
        }

        setErrorMessage("");

        onSubmit(name, description, aiProvider, selectedFiles);
        setName("");
        setDescription("");
        setAiProvider("gemini");
        setSelectedFiles([]);
        
        onClose();
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
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[70%] h-[70%] bg-white rounded-lg shadow-lg p-8 flex flex-row gap-6">
                {/* Left side - Form fields (70%) */}
                <div className="flex flex-col gap-6 flex-1 w-[70%]">
                    <h1 className="text-2xl font-semibold text-gray-800 text-center">Create New Chatbot</h1>
                    
                    <div className="flex flex-col gap-4 flex-1">
                        {/* Chatbot Name */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-gray-700">Chatbot Name</label>
                            <input 
                                type="text"
                                placeholder="Enter chatbot name"
                                className="w-full p-3 border text-black border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                            />
                        </div>
                        
                        {/* Description */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-gray-700">Description</label>
                            <input 
                                type="text"
                                placeholder="Enter chatbot description"
                                className="w-full p-3 border text-black border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
                        </div>

                        {/* AI Provider selection */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-gray-700">AI Provider</label>
                            <div className="flex gap-4">
                                <div className="flex items-center">
                                    <input 
                                        type="radio"
                                        id="gemini"
                                        name="aiProvider"
                                        value="gemini"
                                        className="mr-2"
                                        defaultChecked
                                        onChange={(e) => setAiProvider(e.target.value)}
                                    />
                                    <label htmlFor="gemini" className="text-sm text-gray-700 cursor-pointer">Gemini</label>
                                </div>
                                <div className="flex items-center">
                                    <input 
                                        type="radio"
                                        id="openai"
                                        name="aiProvider"
                                        value="openai"
                                        className="mr-2"
                                        onChange={(e) => setAiProvider(e.target.value)}
                                    />
                                    <label htmlFor="openai" className="text-sm text-gray-700 cursor-pointer">OpenAI</label>
                                </div>
                            </div>
                        </div>

                        {/* Files upload (only PDFs, DOCS, CSVs and TXT) */}
                        <div className="flex flex-col gap-2">
                            <label className="text-sm font-medium text-gray-700">Files</label>
                            <div className="relative">
                                <input 
                                    ref={fileInputRef}
                                    type="file" 
                                    multiple 
                                    onChange={handleFileChange}
                                    accept=".pdf,.doc,.docx,.csv,.txt"
                                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                />
                                <div className="w-full p-3 border text-black border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white cursor-pointer flex items-center gap-2">
                                    <span className="material-symbols-outlined text-gray-500">upload_file</span>
                                    <span className="text-gray-700">Choose files (PDF, DOC, CSV, TXT)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    {/* Error message */}
                    {errorMessage && (
                        <div className="text-red-500 text-sm text-center">
                            {errorMessage}
                        </div>
                    )}

                    <div className="flex justify-center">
                        <button 
                            className="px-8 py-3 bg-[#23272e] text-white rounded-md hover:bg-[#23272e]/80 transition-colors font-medium" 
                            onClick={handleSubmit}
                        >
                            Create Agent
                        </button>
                    </div>
                </div>

                {/* Right side - Files preview (30%) */}
                <div className="w-[30%] flex flex-col gap-4">
                    <h2 className="text-lg font-medium text-gray-800 text-center">Selected Files</h2>
                    <div className="flex-1 border border-gray-200 rounded-md p-4 bg-gray-50 overflow-y-auto">
                        <div className="flex flex-col gap-3">
                            {selectedFiles.length > 0 ? (
                                selectedFiles.map((file, index) => {
                                    const { icon, color } = getFileIcon(file.name);
                                    const fileType = file.name.split('.').pop()?.toUpperCase() || 'FILE';
                                    
                                    return (
                                        <div key={index} className="flex items-center gap-3 p-3 bg-white rounded-md border border-gray-200 shadow-sm">
                                            <div className="flex-shrink-0">
                                                <span className={`material-symbols-outlined ${color}`}>{icon}</span>
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-gray-900 truncate" title={file.name}>
                                                    {file.name}
                                                </p>
                                                <p className="text-xs text-gray-500">{fileType}</p>
                                            </div>
                                            <button 
                                                onClick={() => removeFile(index)}
                                                className="flex-shrink-0 text-gray-400 hover:text-red-500 transition-colors"
                                            >
                                                <span className="material-symbols-outlined text-sm">close</span>
                                            </button>
                                        </div>
                                    );
                                })
                            ) : (
                                /* Empty state when no files */
                                <div className="text-center py-8 text-gray-400">
                                    <span className="material-symbols-outlined text-4xl mb-2 block">upload_file</span>
                                    <p className="text-sm">No files selected</p>
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