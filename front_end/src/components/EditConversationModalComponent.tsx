import { useState, useEffect } from "react";
import { FaTimes } from "react-icons/fa";
import ViewStore from "../stores/ViewStore";

interface EditConversationModalProps {
    open: boolean;
    onClose: () => void;
    currentName: string;
    onSave: (newName: string) => Promise<void>;
    loading?: boolean;
}

const EditConversationModalComponent = ({
    open,
    onClose,
    currentName,
    onSave,
    loading = false
}: EditConversationModalProps) => {
    const [newName, setNewName] = useState("");
    const [wordCount, setWordCount] = useState(0);
    const [isValid, setIsValid] = useState(true);
    const [localLoading, setLocalLoading] = useState(false);
    const { addError } = ViewStore();

    // Reset state when modal opens
    useEffect(() => {
        if (open) {
            setNewName(currentName);
            updateWordCount(currentName);
        }
    }, [open, currentName]);

    const updateWordCount = (text: string) => {
        const words = text.trim().split(/\s+/).filter(word => word.length > 0);
        const count = text.trim() === "" ? 0 : words.length;
        setWordCount(count);
        setIsValid(count <= 10 && count > 0);
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setNewName(value);
        updateWordCount(value);
    };

    const handleSave = async () => {
        if (!isValid) {
            if (wordCount === 0) {
                addError("Conversation name cannot be empty");
            } else {
                addError("Error: The name of the conversation cannot contain more than 10 words");
            }
            return;
        }

        if (newName.trim() === currentName.trim()) {
            onClose();
            return;
        }

        setLocalLoading(true);
        try {
            await onSave(newName.trim());
            onClose();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to update conversation name";
            addError(errorMessage);
        } finally {
            setLocalLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && isValid && !localLoading && !loading) {
            handleSave();
        } else if (e.key === 'Escape') {
            onClose();
        }
    };

    if (!open) return null;

    const actualLoading = loading || localLoading;

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="glass-card w-full max-w-md p-6 relative">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-medium glass-text">Edit Conversation Name</h2>
                    <button
                        onClick={onClose}
                        disabled={actualLoading}
                        className="glass-text hover:glass-light p-1 rounded disabled:opacity-50"
                        aria-label="Close modal"
                    >
                        <FaTimes size={20} />
                    </button>
                </div>

                {/* Input Field */}
                <div className="mb-4">
                    <label className="block text-sm font-medium glass-text mb-2">
                        Conversation Name
                    </label>
                    <input
                        type="text"
                        value={newName}
                        onChange={handleInputChange}
                        onKeyDown={handleKeyPress}
                        disabled={actualLoading}
                        className={`w-full p-3 glass-input text-sm rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 ${!isValid ? 'border-2 border-red-400' : ''
                            }`}
                        placeholder="Enter conversation name..."
                        autoFocus
                        maxLength={200} // Reasonable character limit
                    />

                    {/* Word Count and Validation */}
                    <div className="mt-2 flex justify-between items-center text-xs">
                        <span className={`glass-text ${wordCount > 10 ? 'text-red-300' : 'opacity-70'}`}>
                            {wordCount}/10 words
                        </span>
                        {!isValid && wordCount > 0 && (
                            <span className="text-red-300">Too many words</span>
                        )}
                        {wordCount === 0 && (
                            <span className="text-red-300">Name cannot be empty</span>
                        )}
                    </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3 justify-end">
                    <button
                        onClick={onClose}
                        disabled={actualLoading}
                        className="px-4 py-2 text-sm glass-text hover:glass-light rounded-md transition-colors disabled:opacity-50"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={!isValid || actualLoading || newName.trim() === currentName.trim()}
                        className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {actualLoading && (
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        )}
                        Save
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EditConversationModalComponent;
