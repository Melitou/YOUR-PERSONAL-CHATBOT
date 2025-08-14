import { create } from "zustand";

// To manage UI related states

interface ViewState {
    sidebarOpen: boolean;
    errors: string[];
    currentView: 'chat' | 'organizations';
    setSidebarOpen: (sidebarOpen: boolean) => void;
    setCurrentView: (view: 'chat' | 'organizations') => void;
    addError: (error: string) => void;
    dismissError: (index: number) => void;
    clearAllErrors: () => void;
    resetStore: () => void;
}

const ViewStore = create<ViewState>((set, get) => ({

    sidebarOpen: true,
    errors: [],
    currentView: 'chat' as const,

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

    dismissError: (index: number) => set((state) => ({
        errors: state.errors.filter((_, i) => i !== index)
    })),

    clearAllErrors: () => set({ errors: [] }),

    resetStore: () => set({
        sidebarOpen: false,
        errors: [],
        currentView: 'chat' as const,
    }),

}));

// Initialize browser history management
if (typeof window !== 'undefined') {
    window.addEventListener('popstate', (event) => {
        const state = event.state;
        if (state && state.view) {
            ViewStore.getState().setCurrentView(state.view);
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