import { Modal } from "@mui/material";
import { useState, useEffect } from "react";
import React from "react";

import ViewStore from "../stores/ViewStore";
import ClientOrganizationManagerStore from "../stores/ClientOrganizationManagerStore";

// TypeScript Interfaces
export interface ChatbotUsage {
    chatbotId: string;
    chatbotName: string;
    namespace: string;
    usageCount: number;
    lastUsed: Date;
}

export interface ClientOrganization {
    id: string;
    firstName: string;
    lastName: string;
    email: string;
    organization: string;
    role: 'User' | 'Super User';
    createdAt: Date;
    chatbotUsage: ChatbotUsage[];
    totalUsage: number;
}

const ManageClientOrganizationsModalComponent = ({
    open,
    onClose
}: {
    open: boolean,
    onClose: () => void
}) => {
    const { addError } = ViewStore();
    const {
        clients,
        isLoading,
        error,
        fetchClients,
        removeClient
    } = ClientOrganizationManagerStore();
    const [expandedClient, setExpandedClient] = useState<string | null>(null);

    // Fetch clients when modal opens
    useEffect(() => {
        if (open) {
            fetchClients().catch((error) => {
                const errorMsg = 'Failed to load clients';
                console.error('Error fetching clients on mount:', error);
                addError(errorMsg);
            });
        }
    }, [open, fetchClients, addError]);

    const toggleExpanded = (clientId: string) => {
        setExpandedClient(expandedClient === clientId ? null : clientId);
    };

    const getUsageSummary = (usage: ChatbotUsage[]): string => {
        const chatbotCount = usage.length;
        const totalInteractions = usage.reduce((sum, bot) => sum + bot.usageCount, 0);

        if (chatbotCount === 0) return 'No chatbot usage';
        if (chatbotCount === 1) return `Using 1 chatbot • ${totalInteractions} interactions`;
        return `Using ${chatbotCount} chatbots • ${totalInteractions} interactions`;
    };

    const handleDeleteClient = async (e: React.MouseEvent, clientId: string, clientName: string) => {
        e.stopPropagation();

        const confirmMessage = `Are you sure you want to permanently delete "${clientName}"?\n\n⚠️ WARNING: This action will:\n• Delete the user account permanently\n• Remove all chatbot usage data\n• Cannot be undone\n\nThis action cannot be undone.`;

        if (window.confirm(confirmMessage)) {
            try {
                await removeClient(clientId);
                console.log(`Successfully deleted client: ${clientName}`);
            } catch (error) {
                const errorMsg = `Failed to delete client "${clientName}"`;
                console.error('Delete client error:', error);
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
            <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-[80%] h-[80%] glass-card shadow-lg p-8">
                <div className="flex flex-col gap-6 h-full">
                    {/* Header */}
                    <div className="border-b border-gray-200 px-6 py-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-4">
                                <h2 className="text-xl font-semibold glass-text">
                                    Client & Organization Management ({clients.length})
                                </h2>
                                <span className="text-sm glass-text opacity-70">
                                    Real-time Data
                                </span>
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
                    <div className="flex-1 overflow-y-auto max-h-[calc(80vh-120px)]">
                        {/* Loading State */}
                        {isLoading ? (
                            <div className="flex flex-col items-center justify-center py-12 px-6 h-full">
                                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                                <p className="glass-text opacity-70 text-center">Loading clients...</p>
                            </div>
                        ) :
                            /* Error State */
                            error ? (
                                <div className="flex flex-col items-center justify-center py-12 px-6 h-full">
                                    <span className="material-symbols-outlined text-6xl text-red-300 mb-4 text-center">
                                        error
                                    </span>
                                    <h3 className="text-lg font-medium glass-text mb-2">
                                        Error loading clients
                                    </h3>
                                    <p className="glass-text opacity-70 text-center mb-4">
                                        {error}
                                    </p>
                                    <button
                                        onClick={() => window.location.reload()}
                                        className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                                    >
                                        Retry
                                    </button>
                                </div>
                            ) :
                                /* Empty State */
                                clients.length === 0 ? (
                                    <div className="flex flex-col items-center justify-center py-12 px-6 h-full">
                                        <span className="material-symbols-outlined text-6xl text-gray-300 mb-4 text-center">
                                            group
                                        </span>
                                        <h3 className="text-lg font-medium glass-text mb-2">
                                            No clients registered
                                        </h3>
                                        <p className="glass-text opacity-70 text-center">
                                            No users have registered to use your chatbots yet.
                                        </p>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
                                        {clients.map((client) => (
                                            <div key={client.id} className="p-6">
                                                {/* Client List Item */}
                                                <div
                                                    className="cursor-pointer hover:glass p-4 rounded-lg transition-colors"
                                                    onClick={() => toggleExpanded(client.id)}
                                                >
                                                    <div className="flex items-center justify-between">
                                                        <div className="flex items-center space-x-4">
                                                            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${client.role === 'Super User' ? 'bg-purple-100' : 'bg-blue-100'
                                                                }`}>
                                                                <span className={`material-symbols-outlined ${client.role === 'Super User' ? 'text-purple-600' : 'text-blue-600'
                                                                    }`}>
                                                                    person
                                                                </span>
                                                            </div>
                                                            <div>
                                                                <h3 className="text-lg font-medium glass-text">
                                                                    {client.firstName} {client.lastName}
                                                                </h3>
                                                                <p className="text-sm glass-text opacity-80 mb-1">
                                                                    {client.email}
                                                                </p>
                                                                <p className="text-sm glass-text opacity-70">
                                                                    Organization: {client.organization}
                                                                </p>
                                                                <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-2">
                                                                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${client.role === 'Super User'
                                                                        ? 'bg-purple-100 text-purple-800'
                                                                        : 'bg-blue-100 text-blue-800'
                                                                        }`}>
                                                                        {client.role}
                                                                    </span>
                                                                    <span className="text-xs glass-text opacity-70">
                                                                        {getUsageSummary(client.chatbotUsage)}
                                                                    </span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div className="flex items-center space-x-2">
                                                            <button
                                                                onClick={(e) => handleDeleteClient(e, client.id, `${client.firstName} ${client.lastName}`)}
                                                                className="px-3 py-1 bg-red-100 text-red-800 text-xs rounded-md hover:bg-red-200 transition-colors"
                                                                title="Delete client"
                                                            >
                                                                Delete
                                                            </button>
                                                            <span className={`material-symbols-outlined transform transition-transform ${expandedClient === client.id ? 'rotate-180' : ''
                                                                }`}>
                                                                expand_more
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* Expanded Details */}
                                                {expandedClient === client.id && (
                                                    <div className="mt-4 p-4 glass rounded-lg">
                                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                            {/* Left Column - Client Information */}
                                                            <div>
                                                                <h4 className="text-sm font-semibold glass-text mb-3">
                                                                    Client Information
                                                                </h4>
                                                                <div className="space-y-3">
                                                                    <div>
                                                                        <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                            Full Name
                                                                        </span>
                                                                        <p className="text-sm glass-text mt-1">
                                                                            {client.firstName} {client.lastName}
                                                                        </p>
                                                                    </div>
                                                                    <div>
                                                                        <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                            Email Address
                                                                        </span>
                                                                        <p className="text-sm glass-text mt-1">
                                                                            {client.email}
                                                                        </p>
                                                                    </div>
                                                                    <div>
                                                                        <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                            Organization
                                                                        </span>
                                                                        <p className="text-sm glass-text mt-1">
                                                                            {client.organization}
                                                                        </p>
                                                                    </div>
                                                                    <div>
                                                                        <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                            Account Role
                                                                        </span>
                                                                        <p className="text-sm glass-text mt-1">
                                                                            {client.role}
                                                                        </p>
                                                                    </div>
                                                                    <div>
                                                                        <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">
                                                                            Account Created
                                                                        </span>
                                                                        <p className="text-sm glass-text mt-1">
                                                                            {client.createdAt.toLocaleString()}
                                                                        </p>
                                                                    </div>
                                                                </div>
                                                            </div>

                                                            {/* Right Column - Chatbot Usage */}
                                                            <div>
                                                                <h4 className="text-sm font-semibold glass-text mb-3">
                                                                    Chatbot Usage ({client.chatbotUsage.length})
                                                                </h4>
                                                                <div className="space-y-2 max-h-48 overflow-y-auto">
                                                                    {client.chatbotUsage.length === 0 ? (
                                                                        <p className="text-sm glass-text opacity-70 italic">
                                                                            No chatbot usage yet
                                                                        </p>
                                                                    ) : (
                                                                        client.chatbotUsage.map((usage) => (
                                                                            <div
                                                                                key={usage.chatbotId}
                                                                                className="flex items-center justify-between p-3 bg-gray-50 rounded border"
                                                                            >
                                                                                <div className="flex items-center space-x-3">
                                                                                    <span className="material-symbols-outlined text-blue-600">
                                                                                        smart_toy
                                                                                    </span>
                                                                                    <div className="flex-1 min-w-0">
                                                                                        <p className="text-sm font-medium glass-text truncate">
                                                                                            {usage.chatbotName}
                                                                                        </p>
                                                                                        <p className="text-xs glass-text opacity-70">
                                                                                            Namespace: {usage.namespace}
                                                                                        </p>
                                                                                        <p className="text-xs glass-text opacity-70">
                                                                                            Last used: {usage.lastUsed.toLocaleDateString()}
                                                                                        </p>
                                                                                    </div>
                                                                                </div>
                                                                                <div className="text-right">
                                                                                    <span className="text-lg font-bold text-blue-600">
                                                                                        {usage.usageCount}
                                                                                    </span>
                                                                                    <p className="text-xs glass-text opacity-70">
                                                                                        interactions
                                                                                    </p>
                                                                                </div>
                                                                            </div>
                                                                        ))
                                                                    )}
                                                                </div>

                                                                {client.chatbotUsage.length > 0 && (
                                                                    <div className="mt-3 pt-3 border-t border-gray-200">
                                                                        <div className="flex justify-between text-sm glass-text">
                                                                            <span className="font-medium">Total Interactions:</span>
                                                                            <span className="font-bold text-blue-600">
                                                                                {client.totalUsage}
                                                                            </span>
                                                                        </div>
                                                                    </div>
                                                                )}
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

export default ManageClientOrganizationsModalComponent;
