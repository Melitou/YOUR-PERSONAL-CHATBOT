import { create } from "zustand";

// To manage UI related states

export interface ThinkingStep {
    id: string;
    step: string;
    message: string;
    timestamp: string;
}

export interface ThinkingData {
    isActive: boolean;
    currentMessage: string;
    steps: ThinkingStep[];
    startMessage?: string;
    completeMessage?: string;
    startTime?: string;
    endTime?: string;
}

interface ViewState {
    sidebarOpen: boolean;
    errors: string[];
    successes: string[];
    currentView: 'chat' | 'organizations';
    setSidebarOpen: (sidebarOpen: boolean) => void;
    setCurrentView: (view: 'chat' | 'organizations') => void;
    navigateToHome: () => void;
    addError: (error: string) => void;
    addSuccess: (message: string) => void;
    dismissError: (index: number) => void;
    dismissSuccess: (index: number) => void;
    clearAllErrors: () => void;
    clearAllSuccesses: () => void;
    resetStore: () => void;

    thoughtVisualizerOpen: boolean;
    setThoughtVisualizerOpen: (thoughtVisualizerOpen: boolean) => void;
    thoughtVisualizerData: ThinkingData;
    setThoughtVisualizerData: (thoughtVisualizerData: ThinkingData) => void;
    addThinkingStart: (message: string) => void;
    addThinkingStep: (step: string, message: string) => void;
    completeThinking: (message: string) => void;
    resetThinking: () => void;
}

const ViewStore = create<ViewState>((set, get) => ({

    sidebarOpen: true,
    errors: [],
    successes: [],
    currentView: 'chat' as const,
    thoughtVisualizerOpen: false,
    thoughtVisualizerData: {
        isActive: false,
        currentMessage: '',
        steps: [],
        startMessage: undefined,
        completeMessage: undefined,
        startTime: undefined,
        endTime: undefined
    },

    setSidebarOpen: (sidebarOpen: boolean) => set({ sidebarOpen }),

    setCurrentView: (view: 'chat' | 'organizations') => {
        set({ currentView: view });
        // Update browser history
        if (view === 'organizations') {
            window.history.pushState({ view: 'organizations' }, '', '#organizations');
            document.title = 'Organizations - Your Personal Chatbot';
        } else {
            window.history.pushState({ view: 'chat' }, '', '#chat');
            document.title = 'Your Personal Chatbot';
        }
    },

    navigateToHome: () => {
        // Import LoadedChatbotStore dynamically to avoid circular imports
        import('../stores/LoadedChatbotStore').then((module) => {
            const LoadedChatbotStore = module.default;
            // Clear the loaded chatbot to return to welcome screen
            (LoadedChatbotStore.getState() as any).resetStore();
        });

        // Set view to chat (which will show welcome screen when no chatbot is loaded)
        set({ currentView: 'chat' });

        // Close sidebar
        set({ sidebarOpen: false });

        // Update browser history to home
        window.history.pushState({ view: 'home' }, '', '/');
        document.title = 'Your Personal Chatbot';
    },

    addError: (error: string) => {
        console.error('Error logged:', error);
        set((state) => ({
            errors: [...state.errors, error]
        }));

        // Auto-dismiss error after 10 seconds
        setTimeout(() => {
            const currentErrors = get().errors;
            const errorIndex = currentErrors.indexOf(error);
            if (errorIndex !== -1) {
                get().dismissError(errorIndex);
            }
        }, 10000);
    },

    addSuccess: (message: string) => {
        console.log('Success logged:', message);
        set((state) => ({
            successes: [...state.successes, message]
        }));

        // Auto-dismiss success after 5 seconds
        setTimeout(() => {
            const currentSuccesses = get().successes;
            const successIndex = currentSuccesses.indexOf(message);
            if (successIndex !== -1) {
                get().dismissSuccess(successIndex);
            }
        }, 5000);
    },

    dismissError: (index: number) => set((state) => ({
        errors: state.errors.filter((_, i) => i !== index)
    })),

    dismissSuccess: (index: number) => set((state) => ({
        successes: state.successes.filter((_, i) => i !== index)
    })),

    clearAllErrors: () => set({ errors: [] }),

    clearAllSuccesses: () => set({ successes: [] }),

    resetStore: () => set({
        sidebarOpen: false,
        errors: [],
        successes: [],
        currentView: 'chat' as const,
        thoughtVisualizerOpen: false,
        thoughtVisualizerData: {
            isActive: false,
            currentMessage: '',
            steps: [],
            startMessage: undefined,
            completeMessage: undefined,
            startTime: undefined,
            endTime: undefined
        }
    }),

    setThoughtVisualizerOpen: (thoughtVisualizerOpen: boolean) => set({ thoughtVisualizerOpen }),

    setThoughtVisualizerData: (thoughtVisualizerData: ThinkingData) => set({ thoughtVisualizerData }),

    addThinkingStart: (message: string) => {
        const timestamp = new Date().toISOString();
        set(state => ({
            thoughtVisualizerData: {
                ...state.thoughtVisualizerData,
                isActive: true,
                startMessage: message,
                currentMessage: message,
                startTime: timestamp,
                steps: [],
                completeMessage: undefined,
                endTime: undefined
            }
        }));
    },

    addThinkingStep: (step: string, message: string) => {
        const timestamp = new Date().toISOString();
        const stepId = `step-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        set(state => ({
            thoughtVisualizerData: {
                ...state.thoughtVisualizerData,
                currentMessage: message,
                steps: [...state.thoughtVisualizerData.steps, {
                    id: stepId,
                    step,
                    message,
                    timestamp
                }]
            }
        }));
    },

    completeThinking: (message: string) => {
        const timestamp = new Date().toISOString();
        set(state => ({
            thoughtVisualizerData: {
                ...state.thoughtVisualizerData,
                isActive: false,
                completeMessage: message,
                currentMessage: message,
                endTime: timestamp
            }
        }));
    },

    resetThinking: () => {
        set(() => ({
            thoughtVisualizerData: {
                isActive: false,
                currentMessage: '',
                steps: [],
                startMessage: undefined,
                completeMessage: undefined,
                startTime: undefined,
                endTime: undefined
            }
        }));
    },

}));

// Initialize browser history management
if (typeof window !== 'undefined') {
    window.addEventListener('popstate', (event) => {
        const state = event.state;
        if (state && state.view) {
            if (state.view === 'home') {
                ViewStore.getState().navigateToHome();
            } else {
                ViewStore.getState().setCurrentView(state.view);
            }
        } else {
            // Default to chat view when no state
            ViewStore.setState({ currentView: 'chat' });
            document.title = 'Your Personal Chatbot';
        }
    });

    // Handle initial page load - check URL hash
    window.addEventListener('load', () => {
        if (window.location.hash === '#organizations') {
            ViewStore.getState().setCurrentView('organizations');
        }
    });
}

export default ViewStore;