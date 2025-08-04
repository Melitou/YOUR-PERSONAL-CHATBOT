import { create } from "zustand";

// To manage UI related states

interface ViewState {
    sidebarOpen: boolean;
    errors: string[];
    setSidebarOpen: (sidebarOpen: boolean) => void;
    addError: (error: string) => void;
    dismissError: (index: number) => void;
    clearAllErrors: () => void;
    resetStore: () => void;
}

const ViewStore = create<ViewState>((set, get) => ({
    
    sidebarOpen: false,
    errors: [],
    
    setSidebarOpen: (sidebarOpen: boolean) => set({ sidebarOpen }),
    
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
    }),

}));

export default ViewStore;