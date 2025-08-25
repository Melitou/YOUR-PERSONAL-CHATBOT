import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { clientApi } from '../utils/api';
import ViewStore from '../stores/ViewStore';

interface AssignedClient {
    client_id: string;
    user_name: string;
    first_name: string;
    last_name: string;
    email: string;
    assigned_at: string;
    is_active: boolean;
}

interface AssignClientsModalProps {
    open: boolean;
    onClose: () => void;
    chatbotId: string;
    chatbotName: string;
}

const AssignClientsModalComponent: React.FC<AssignClientsModalProps> = ({
    open,
    onClose,
    chatbotId,
    chatbotName
}) => {
    const [clientEmail, setClientEmail] = useState('');
    const [assignedClients, setAssignedClients] = useState<AssignedClient[]>([]);
    const [loading, setLoading] = useState(false);
    const [addingClient, setAddingClient] = useState(false);
    const { addSuccess, addError } = ViewStore();

    useEffect(() => {
        if (open) {
            fetchAssignedClients();
        }
    }, [open, chatbotId]);

    const fetchAssignedClients = async () => {
        setLoading(true);
        try {
            const assignments = await clientApi.getChatbotAssignments(chatbotId);
            setAssignedClients(assignments);
        } catch (error: any) {
            console.error('Failed to fetch assigned clients:', error);
            addError('Failed to load assigned clients');
        } finally {
            setLoading(false);
        }
    };

    const handleAddClient = async () => {
        if (!clientEmail.trim()) {
            addError('Please enter a valid email address');
            return;
        }

        if (!isValidEmail(clientEmail)) {
            addError('Please enter a valid email format');
            return;
        }

        setAddingClient(true);
        try {
            await clientApi.assignChatbotByEmail(chatbotId, clientEmail.trim());

            addSuccess(`Chatbot assigned to existing client ${clientEmail}`);

            setClientEmail('');
            await fetchAssignedClients(); // Refresh the list
        } catch (error: any) {
            console.error('Failed to assign chatbot:', error);
            addError(error.message || 'Failed to assign chatbot to client');
        } finally {
            setAddingClient(false);
        }
    };

    const handleRemoveClient = async (clientEmail: string) => {
        if (!confirm(`Remove chatbot access from ${clientEmail}?`)) {
            return;
        }

        try {
            await clientApi.revokeChatbotFromClient(chatbotId, clientEmail);
            addSuccess(`Chatbot access revoked from ${clientEmail}`);
            await fetchAssignedClients(); // Refresh the list
        } catch (error: any) {
            console.error('Failed to revoke chatbot:', error);
            addError(error.message || 'Failed to revoke chatbot access');
        }
    };

    const isValidEmail = (email: string) => {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !addingClient && isValidEmail(clientEmail)) {
            handleAddClient();
        }
    };

    if (!open) return null;

    const modalContent = (
        <div
            className="fixed inset-0 z-[1400] flex items-center justify-center p-4"
            style={{
                backdropFilter: 'blur(5px)',
                backgroundColor: 'rgba(0, 0, 0, 0.5)'
            }}
            onClick={(e) => {
                if (e.target === e.currentTarget) {
                    onClose();
                }
            }}
        >
            <div
                className="glass-card shadow-xl max-w-2xl w-full max-h-[80vh] overflow-hidden"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="p-6 border-b border-gray-200 border-opacity-20">
                    <div className="flex items-center justify-between">
                        <h2 className="text-xl font-semibold glass-text">
                            Manage Client Access
                        </h2>
                        <button
                            onClick={onClose}
                            className="glass-text opacity-60 hover:opacity-80 transition-colors p-1"
                        >
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                    </div>
                    <p className="text-sm glass-text opacity-70 mt-1">
                        Chatbot: <span className="font-medium">{chatbotName}</span>
                    </p>
                </div>

                <div className="p-6 overflow-y-auto flex-1">
                    {/* Add new client section */}
                    <div className="mb-6">
                        <h3 className="text-lg font-medium glass-text mb-3">
                            Add Client by Email
                        </h3>
                        <div className="flex gap-3">
                            <input
                                type="email"
                                value={clientEmail}
                                onChange={(e) => setClientEmail(e.target.value)}
                                onKeyPress={handleKeyPress}
                                placeholder="Enter client email address"
                                className={`flex-1 px-3 py-2 glass-dark rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent glass-text ${clientEmail.trim() !== '' && !isValidEmail(clientEmail)
                                    ? 'border-red-300 bg-red-50'
                                    : ''
                                    }`}
                                disabled={addingClient}
                                autoFocus
                            />
                            <button
                                onClick={handleAddClient}
                                disabled={addingClient || !isValidEmail(clientEmail) || !clientEmail.trim()}
                                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors min-w-[80px]"
                            >
                                {addingClient ? (
                                    <div className="flex items-center">
                                        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                                        Adding
                                    </div>
                                ) : (
                                    'Add'
                                )}
                            </button>
                        </div>
                        <p className="text-xs glass-text opacity-70 mt-2">
                            {clientEmail.trim() !== '' && !isValidEmail(clientEmail)
                                ? 'Please enter a valid email address'
                                : 'If client doesn\'t exist, a new account will be created automatically'
                            }
                        </p>
                    </div>

                    {/* Currently assigned clients */}
                    <div>
                        <h3 className="text-lg font-medium glass-text mb-3">
                            Currently Assigned Clients ({assignedClients.length})
                        </h3>

                        {loading ? (
                            <div className="text-center py-8">
                                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
                                <div className="glass-text opacity-70 mt-2">Loading...</div>
                            </div>
                        ) : assignedClients.length === 0 ? (
                            <div className="text-center py-8 glass rounded-lg">
                                <div className="w-12 h-12 glass-dark rounded-full flex items-center justify-center mx-auto mb-3">
                                    <svg className="w-6 h-6 glass-text opacity-60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                                    </svg>
                                </div>
                                <p className="glass-text opacity-70">No clients assigned yet</p>
                                <p className="text-sm glass-text opacity-50 mt-1">Add a client email above to get started</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {assignedClients.map(client => (
                                    <div
                                        key={client.client_id}
                                        className="flex items-center justify-between p-4 glass-dark rounded-lg hover:glass-light transition-colors"
                                    >
                                        <div className="flex items-center">
                                            <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center mr-3">
                                                <span className="text-blue-600 font-medium text-sm">
                                                    {client.email[0].toUpperCase()}
                                                </span>
                                            </div>
                                            <div>
                                                <div className="font-medium glass-text">
                                                    {client.first_name && client.last_name
                                                        ? `${client.first_name} ${client.last_name}`
                                                        : client.user_name
                                                    }
                                                </div>
                                                <div className="text-sm glass-text opacity-80">
                                                    {client.email}
                                                </div>
                                                <div className="text-xs glass-text opacity-60">
                                                    Assigned: {new Date(client.assigned_at).toLocaleDateString('en-US', {
                                                        year: 'numeric',
                                                        month: 'short',
                                                        day: 'numeric',
                                                        hour: '2-digit',
                                                        minute: '2-digit'
                                                    })}
                                                </div>
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => handleRemoveClient(client.email)}
                                            className="p-2 text-red-400 hover:text-red-300 hover:glass rounded-md transition-colors"
                                            title="Remove access"
                                        >
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                            </svg>
                                        </button>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );

    // Use portal to render modal at document body level to avoid MUI Modal focus issues
    return createPortal(modalContent, document.body);
};

export default AssignClientsModalComponent;
