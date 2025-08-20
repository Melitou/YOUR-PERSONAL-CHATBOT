import { useState } from "react";
import { FaTimes, FaExclamationTriangle } from "react-icons/fa";
import ViewStore from "../stores/ViewStore";

interface DeleteConversationModalProps {
    open: boolean;
    onClose: () => void;
    conversationName: string;
    onConfirm: () => Promise<void>;
    loading?: boolean;
}

const DeleteConversationModalComponent = ({
    open,
    onClose,
    conversationName,
    onConfirm,
    loading = false
}: DeleteConversationModalProps) => {
    const [localLoading, setLocalLoading] = useState(false);
    const { addError } = ViewStore();

    const handleConfirm = async () => {
        setLocalLoading(true);
        try {
            await onConfirm();
            onClose();
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : "Failed to delete conversation";
            addError(errorMessage);
        } finally {
            setLocalLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !actualLoading) {
            handleConfirm();
        } else if (e.key === 'Escape') {
            onClose();
        }
    };

    if (!open) return null;

    const actualLoading = loading || localLoading;

    return (
        <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            onKeyDown={handleKeyPress}
            tabIndex={-1}
        >
            <div className="glass-card w-full max-w-md p-6 relative">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-red-500/20 rounded-full">
                            <FaExclamationTriangle className="text-red-400" size={20} />
                        </div>
                        <h2 className="text-xl font-medium glass-text">Delete Conversation</h2>
                    </div>
                    <button
                        onClick={onClose}
                        disabled={actualLoading}
                        className="glass-text hover:glass-light p-1 rounded disabled:opacity-50"
                        aria-label="Close modal"
                    >
                        <FaTimes size={20} />
                    </button>
                </div>

                {/* Warning Message */}
                <div className="mb-6">
                    <p className="glass-text text-sm mb-3">
                        Are you sure you want to delete this conversation? This action cannot be undone.
                    </p>

                    <div className="p-3 bg-red-500/10 border border-red-400/30 rounded-md">
                        <p className="glass-text text-sm font-medium">
                            Conversation: "{conversationName}"
                        </p>
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
                        onClick={handleConfirm}
                        disabled={actualLoading}
                        className="px-4 py-2 text-sm bg-red-600 hover:bg-red-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {actualLoading && (
                            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        )}
                        Delete
                    </button>
                </div>
            </div>
        </div>
    );
};

export default DeleteConversationModalComponent;
