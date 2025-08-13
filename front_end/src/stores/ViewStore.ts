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
    setSidebarOpen: (sidebarOpen: boolean) => void;
    addError: (error: string) => void;
    dismissError: (index: number) => void;
    clearAllErrors: () => void;
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
    
    sidebarOpen: false,
    errors: [],
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
    setThoughtVisualizerOpen: (thoughtVisualizerOpen: boolean) => set({ thoughtVisualizerOpen }),
    setThoughtVisualizerData: (thoughtVisualizerData: ThinkingData) => set({ thoughtVisualizerData }),
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

    resetStore: () => set({
        sidebarOpen: false,
        errors: [],
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

}));

export default ViewStore;