import { create } from "zustand";
import ViewStore from "./ViewStore";

// Import interfaces from the component
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

export interface OrganizationSummary {
    name: string;
    clientCount: number;
    totalUsage: number;
    roles: { users: number; superUsers: number };
    clients: ClientOrganization[];
}

interface ClientOrganizationManagerState {
    clients: ClientOrganization[];
    isLoading: boolean;
    error: string | null;
    selectedOrganization: string | null;

    // Computed function
    getOrganizationsGrouped: () => { [organizationName: string]: OrganizationSummary };

    // Actions
    setClients: (clients: ClientOrganization[]) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    deleteClient: (id: string) => void;
    setSelectedOrganization: (orgName: string | null) => void;

    // API integration actions
    fetchClients: () => Promise<void>;
    removeClient: (id: string) => Promise<void>;

    // Reset action
    resetStore: () => void;
}

const ClientOrganizationManagerStore = create<ClientOrganizationManagerState>((set: any, get: any) => ({
    clients: [],
    isLoading: false,
    error: null,
    selectedOrganization: null,

    // Computed function for organizationsGrouped
    getOrganizationsGrouped: () => {
        const clients = get().clients;
        const grouped: { [organizationName: string]: OrganizationSummary } = {};

        clients.forEach((client: any) => {
            const orgName = client.organization;
            if (!grouped[orgName]) {
                grouped[orgName] = {
                    name: orgName,
                    clientCount: 0,
                    totalUsage: 0,
                    roles: { users: 0, superUsers: 0 },
                    clients: []
                };
            }

            grouped[orgName].clientCount++;
            grouped[orgName].totalUsage += client.totalUsage;
            grouped[orgName].clients.push(client);

            if (client.role === 'Super User') {
                grouped[orgName].roles.superUsers++;
            } else {
                grouped[orgName].roles.users++;
            }
        });

        return grouped;
    },

    // Basic state management
    setClients: (clients: any) => {
        set({ clients, error: null });
    },

    setLoading: (isLoading: any) => {
        set({ isLoading });
    },

    setError: (error: any) => {
        set({ error, isLoading: false });
    },

    deleteClient: (id: any) => {
        set((state: any) => ({
            clients: state.clients.filter((client: any) => client.id !== id),
            error: null
        }));
    },

    setSelectedOrganization: (orgName: any) => {
        set({ selectedOrganization: orgName });
    },

    // API integration methods
    fetchClients: async () => {
        try {
            set({ isLoading: true, error: null });

            // For now, create mock data - will be replaced with real API call
            const mockClients: ClientOrganization[] = [
                {
                    id: "client-1",
                    firstName: "John",
                    lastName: "Doe",
                    email: "john.doe@acme.com",
                    organization: "ACME Corporation",
                    role: "User",
                    createdAt: new Date("2024-01-15"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-1",
                            chatbotName: "Customer Support Bot",
                            namespace: "support_bot_acme",
                            usageCount: 45,
                            lastUsed: new Date("2024-12-01")
                        },
                        {
                            chatbotId: "bot-2",
                            chatbotName: "Product Info Bot",
                            namespace: "product_bot_acme",
                            usageCount: 23,
                            lastUsed: new Date("2024-11-28")
                        }
                    ],
                    totalUsage: 68
                },
                {
                    id: "client-2",
                    firstName: "Jane",
                    lastName: "Smith",
                    email: "jane.smith@techcorp.com",
                    organization: "TechCorp Inc",
                    role: "Super User",
                    createdAt: new Date("2024-02-20"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-3",
                            chatbotName: "HR Assistant",
                            namespace: "hr_bot_techcorp",
                            usageCount: 89,
                            lastUsed: new Date("2024-12-02")
                        }
                    ],
                    totalUsage: 89
                },
                {
                    id: "client-3",
                    firstName: "Bob",
                    lastName: "Johnson",
                    email: "bob.johnson@startup.io",
                    organization: "StartupXYZ",
                    role: "User",
                    createdAt: new Date("2024-03-10"),
                    chatbotUsage: [],
                    totalUsage: 0
                },
                {
                    id: "client-4",
                    firstName: "Alice",
                    lastName: "Brown",
                    email: "alice.brown@acme.com",
                    organization: "ACME Corporation",
                    role: "Super User",
                    createdAt: new Date("2024-01-20"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-1",
                            chatbotName: "Customer Support Bot",
                            namespace: "support_bot_acme",
                            usageCount: 120,
                            lastUsed: new Date("2024-12-03")
                        }
                    ],
                    totalUsage: 120
                },
                {
                    id: "client-5",
                    firstName: "Maria",
                    lastName: "Maraki",
                    email: "maria.maraki@innovation.gr",
                    organization: "Innovation Labs",
                    role: "Super User",
                    createdAt: new Date("2024-01-10"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-4",
                            chatbotName: "Research Assistant",
                            namespace: "research_bot_innovation",
                            usageCount: 156,
                            lastUsed: new Date("2024-12-04")
                        },
                        {
                            chatbotId: "bot-5",
                            chatbotName: "Project Manager Bot",
                            namespace: "pm_bot_innovation",
                            usageCount: 89,
                            lastUsed: new Date("2024-12-03")
                        }
                    ],
                    totalUsage: 245
                },
                {
                    id: "client-6",
                    firstName: "Nikos",
                    lastName: "Papadopoulos",
                    email: "nikos.papadopoulos@innovation.gr",
                    organization: "Innovation Labs",
                    role: "User",
                    createdAt: new Date("2024-02-15"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-4",
                            chatbotName: "Research Assistant",
                            namespace: "research_bot_innovation",
                            usageCount: 67,
                            lastUsed: new Date("2024-12-02")
                        }
                    ],
                    totalUsage: 67
                },
                {
                    id: "client-7",
                    firstName: "Elena",
                    lastName: "Dimitriou",
                    email: "elena.dimitriou@innovation.gr",
                    organization: "Innovation Labs",
                    role: "User",
                    createdAt: new Date("2024-03-01"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-5",
                            chatbotName: "Project Manager Bot",
                            namespace: "pm_bot_innovation",
                            usageCount: 34,
                            lastUsed: new Date("2024-11-30")
                        }
                    ],
                    totalUsage: 34
                },
                {
                    id: "client-8",
                    firstName: "Michael",
                    lastName: "Zhang",
                    email: "michael.zhang@techcorp.com",
                    organization: "TechCorp Inc",
                    role: "User",
                    createdAt: new Date("2024-02-25"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-3",
                            chatbotName: "HR Assistant",
                            namespace: "hr_bot_techcorp",
                            usageCount: 12,
                            lastUsed: new Date("2024-11-25")
                        }
                    ],
                    totalUsage: 12
                },
                {
                    id: "client-9",
                    firstName: "Sarah",
                    lastName: "Wilson",
                    email: "sarah.wilson@startup.io",
                    organization: "StartupXYZ",
                    role: "Super User",
                    createdAt: new Date("2024-03-05"),
                    chatbotUsage: [
                        {
                            chatbotId: "bot-6",
                            chatbotName: "Sales Assistant",
                            namespace: "sales_bot_startup",
                            usageCount: 78,
                            lastUsed: new Date("2024-12-01")
                        }
                    ],
                    totalUsage: 78
                }
            ];

            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 1000));

            set({ clients: mockClients, isLoading: false });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to fetch clients';
            console.error('Failed to fetch clients:', errorMessage);
            ViewStore.getState().addError(errorMessage);
            set({
                error: errorMessage,
                isLoading: false
            });
        }
    },

    removeClient: async (id: any) => {
        try {
            set({ isLoading: true, error: null });

            // TODO: Implement actual API call
            // await adminApi.deleteClient(id);

            // Simulate API delay
            await new Promise(resolve => setTimeout(resolve, 500));

            // Remove from local state on successful deletion
            get().deleteClient(id);
            set({ isLoading: false });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete client';
            console.error('Failed to delete client:', errorMessage);
            ViewStore.getState().addError(errorMessage);
            set({
                error: errorMessage,
                isLoading: false
            });
        }
    },

    resetStore: () => {
        set({
            clients: [],
            isLoading: false,
            error: null,
            selectedOrganization: null
        });
    },
}));

export default ClientOrganizationManagerStore;
