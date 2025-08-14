import { useState, useEffect } from "react";
import ViewStore from "../stores/ViewStore";
import ClientOrganizationManagerStore from "../stores/ClientOrganizationManagerStore";

const OrganizationsPage = () => {
    const { setCurrentView } = ViewStore();
    const {
        getOrganizationsGrouped,
        selectedOrganization,
        setSelectedOrganization,
        isLoading,
        error,
        fetchClients,
        removeClient
    } = ClientOrganizationManagerStore();

    // Get the organizations grouped data
    const organizationsGrouped = getOrganizationsGrouped();

    const [expandedClient, setExpandedClient] = useState<string | null>(null);

    // Fetch clients when page loads
    useEffect(() => {
        fetchClients().catch((error) => {
            console.error('Error fetching clients on mount:', error);
        });
    }, [fetchClients]);

    const handleBackToChat = () => {
        setCurrentView('chat');
        setSelectedOrganization(null);
    };

    const handleBackToOrganizations = () => {
        setSelectedOrganization(null);
        setExpandedClient(null);
    };

    const handleOrganizationClick = (orgName: string) => {
        setSelectedOrganization(orgName);
        setExpandedClient(null);
    };

    const toggleClientExpanded = (clientId: string) => {
        setExpandedClient(expandedClient === clientId ? null : clientId);
    };

    const handleDeleteClient = async (e: React.MouseEvent, clientId: string, clientName: string) => {
        e.stopPropagation();

        const confirmMessage = `Are you sure you want to permanently delete "${clientName}"?\n\n⚠️ WARNING: This action will:\n• Delete the user account permanently\n• Remove all chatbot usage data\n• Cannot be undone\n\nThis action cannot be undone.`;

        if (window.confirm(confirmMessage)) {
            try {
                await removeClient(clientId);
                console.log(`Successfully deleted client: ${clientName}`);
            } catch (error) {
                console.error('Delete client error:', error);
            }
        }
    };

    const getUsageSummary = (usage: any[]): string => {
        const chatbotCount = usage.length;
        const totalInteractions = usage.reduce((sum: number, bot: any) => sum + bot.usageCount, 0);

        if (chatbotCount === 0) return 'No chatbot usage';
        if (chatbotCount === 1) return `Using 1 chatbot • ${totalInteractions} interactions`;
        return `Using ${chatbotCount} chatbots • ${totalInteractions} interactions`;
    };

    // Loading State
    if (isLoading) {
        return (
            <div className="h-full flex flex-col">
                {/* Header */}
                <div className="border-b border-gray-200 px-6 py-4 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <button
                                onClick={handleBackToChat}
                                className="glass-text opacity-60 hover:opacity-80 transition-colors flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined">arrow_back</span>
                                <span className="text-sm">Back to Chat</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Loading Content */}
                <div className="flex-1 flex items-center justify-center">
                    <div className="flex flex-col items-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
                        <p className="glass-text opacity-70">Loading organizations...</p>
                    </div>
                </div>
            </div>
        );
    }

    // Error State
    if (error) {
        return (
            <div className="h-full flex flex-col">
                {/* Header */}
                <div className="border-b border-gray-200 px-6 py-4 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <button
                                onClick={handleBackToChat}
                                className="glass-text opacity-60 hover:opacity-80 transition-colors flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined">arrow_back</span>
                                <span className="text-sm">Back to Chat</span>
                            </button>
                        </div>
                    </div>
                </div>

                {/* Error Content */}
                <div className="flex-1 flex items-center justify-center">
                    <div className="flex flex-col items-center">
                        <span className="material-symbols-outlined text-6xl text-red-300 mb-4">error</span>
                        <h3 className="text-lg font-medium glass-text mb-2">Error loading organizations</h3>
                        <p className="glass-text opacity-70 text-center mb-4">{error}</p>
                        <button
                            onClick={() => window.location.reload()}
                            className="px-4 py-2 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
                        >
                            Retry
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    // Show selected organization's clients
    if (selectedOrganization && organizationsGrouped[selectedOrganization]) {
        const orgData = organizationsGrouped[selectedOrganization];

        return (
            <div className="h-full flex flex-col">
                {/* Header */}
                <div className="border-b border-gray-200 px-6 py-4 flex-shrink-0">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                            <button
                                onClick={handleBackToOrganizations}
                                className="glass-text opacity-60 hover:opacity-80 transition-colors flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined">arrow_back</span>
                                <span className="text-sm">Back to Organizations</span>
                            </button>
                            <div>
                                <h2 className="text-xl font-semibold glass-text">{orgData.name}</h2>
                                <p className="text-sm glass-text opacity-70">
                                    {orgData.clientCount} clients • {orgData.totalUsage} total interactions
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Clients List */}
                <div className="flex-1 overflow-y-auto p-6">
                    {orgData.clients.length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full">
                            <span className="material-symbols-outlined text-6xl text-gray-300 mb-4">group</span>
                            <h3 className="text-lg font-medium glass-text mb-2">No clients in this organization</h3>
                            <p className="glass-text opacity-70 text-center">This organization has no registered users yet.</p>
                        </div>
                    ) : (
                        <div className="space-y-4">
                            {orgData.clients.map((client) => (
                                <div key={client.id} className="border border-gray-200 rounded-lg p-4">
                                    <div
                                        className="cursor-pointer hover:glass p-2 rounded-lg transition-colors"
                                        onClick={() => toggleClientExpanded(client.id)}
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
                                                    <p className="text-sm glass-text opacity-80 mb-1">{client.email}</p>
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

                                    {/* Expanded Client Details */}
                                    {expandedClient === client.id && (
                                        <div className="mt-4 p-4 glass rounded-lg">
                                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                                {/* Left Column - Client Information */}
                                                <div>
                                                    <h4 className="text-sm font-semibold glass-text mb-3">Client Information</h4>
                                                    <div className="space-y-3">
                                                        <div>
                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">Full Name</span>
                                                            <p className="text-sm glass-text mt-1">{client.firstName} {client.lastName}</p>
                                                        </div>
                                                        <div>
                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">Email Address</span>
                                                            <p className="text-sm glass-text mt-1">{client.email}</p>
                                                        </div>
                                                        <div>
                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">Account Role</span>
                                                            <p className="text-sm glass-text mt-1">{client.role}</p>
                                                        </div>
                                                        <div>
                                                            <span className="text-xs font-medium glass-text opacity-70 uppercase tracking-wide">Account Created</span>
                                                            <p className="text-sm glass-text mt-1">{client.createdAt.toLocaleString()}</p>
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
                                                            <p className="text-sm glass-text opacity-70 italic">No chatbot usage yet</p>
                                                        ) : (
                                                            client.chatbotUsage.map((usage) => (
                                                                <div
                                                                    key={usage.chatbotId}
                                                                    className="flex items-center justify-between p-3 bg-gray-50 rounded border"
                                                                >
                                                                    <div className="flex items-center space-x-3">
                                                                        <span className="material-symbols-outlined text-blue-600">smart_toy</span>
                                                                        <div className="flex-1 min-w-0">
                                                                            <p className="text-sm font-medium glass-text truncate">{usage.chatbotName}</p>
                                                                            <p className="text-xs glass-text opacity-70">Namespace: {usage.namespace}</p>
                                                                            <p className="text-xs glass-text opacity-70">Last used: {usage.lastUsed.toLocaleDateString()}</p>
                                                                        </div>
                                                                    </div>
                                                                    <div className="text-right">
                                                                        <span className="text-lg font-bold text-blue-600">{usage.usageCount}</span>
                                                                        <p className="text-xs glass-text opacity-70">interactions</p>
                                                                    </div>
                                                                </div>
                                                            ))
                                                        )}
                                                    </div>

                                                    {client.chatbotUsage.length > 0 && (
                                                        <div className="mt-3 pt-3 border-t border-gray-200">
                                                            <div className="flex justify-between text-sm glass-text">
                                                                <span className="font-medium">Total Interactions:</span>
                                                                <span className="font-bold text-blue-600">{client.totalUsage}</span>
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
        );
    }

    // Show organizations list
    const organizations = Object.values(organizationsGrouped);

    return (
        <div className="h-full flex flex-col">
            {/* Header */}
            <div className="border-b border-gray-200 px-6 py-4 flex-shrink-0">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <button
                            onClick={handleBackToChat}
                            className="glass-text opacity-60 hover:opacity-80 transition-colors flex items-center gap-2"
                        >
                            <span className="material-symbols-outlined">arrow_back</span>
                            <span className="text-sm">Back to Chat</span>
                        </button>
                        <div>
                            <h2 className="text-xl font-semibold glass-text">
                                Organizations ({organizations.length})
                            </h2>
                            <span className="text-sm glass-text opacity-70">Real-time Data</span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Organizations List */}
            <div className="flex-1 overflow-y-auto p-6">
                {organizations.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full">
                        <span className="material-symbols-outlined text-6xl text-gray-300 mb-4">business</span>
                        <h3 className="text-lg font-medium glass-text mb-2">No organizations found</h3>
                        <p className="glass-text opacity-70 text-center">No organizations have registered users yet.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {organizations.map((org) => (
                            <div
                                key={org.name}
                                className="border border-gray-200 rounded-lg p-6 hover:glass cursor-pointer transition-colors"
                                onClick={() => handleOrganizationClick(org.name)}
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center space-x-3">
                                        <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                                            <span className="material-symbols-outlined text-blue-600">business</span>
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold glass-text">{org.name}</h3>
                                            <p className="text-sm glass-text opacity-70">{org.clientCount} clients</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="space-y-3">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm glass-text opacity-70">Total Usage</span>
                                        <span className="text-lg font-bold text-blue-600">{org.totalUsage}</span>
                                    </div>

                                    <div className="flex justify-between items-center">
                                        <span className="text-sm glass-text opacity-70">Users</span>
                                        <span className="text-sm glass-text">{org.roles.users}</span>
                                    </div>

                                    <div className="flex justify-between items-center">
                                        <span className="text-sm glass-text opacity-70">Super Users</span>
                                        <span className="text-sm glass-text">{org.roles.superUsers}</span>
                                    </div>
                                </div>

                                <div className="mt-4 pt-4 border-t border-gray-200">
                                    <div className="flex items-center text-sm text-blue-600 font-medium">
                                        <span>View Details</span>
                                        <span className="material-symbols-outlined ml-1">arrow_forward</span>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrganizationsPage;
