import { create } from "zustand";
import ChatbotManagerStore from "./ChatbotManagerStore";
import LoadedChatbotStore from "./LoadedChatbotStore";
import ViewStore from "./ViewStore";

interface User {
    name: string;
    email?: string;
    role?: string;
}

interface UserAuthState {
    user: User | null;
    isLoggedIn: boolean;
    login: (userData: User, token: string) => void;
    logout: () => void;
    loadPersistedState: () => void;
}

// Helper functions for manual persistence
const STORAGE_KEY = 'user-auth-storage';

const saveToStorage = (state: { user: User | null; isLoggedIn: boolean }) => {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
        console.warn('Failed to save auth state to localStorage:', error);
    }
};

const loadFromStorage = (): { user: User | null; isLoggedIn: boolean } | null => {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored ? JSON.parse(stored) : null;
    } catch (error) {
        console.warn('Failed to load auth state from localStorage:', error);
        return null;
    }
};

const UserAuthStore = create<UserAuthState>((set, get) => ({
    user: null,
    isLoggedIn: false,

    loadPersistedState: () => {
        const persistedState = loadFromStorage();
        if (persistedState) {
            console.log('Loading persisted auth state:', persistedState);
            set({
                user: persistedState.user,
                isLoggedIn: persistedState.isLoggedIn
            });
        }
    },

    login: (userData: User, token: string) => {
        console.log('UserAuthStore login called with:', userData);
        
        // Clear all stores when user logs in
        try {
            (ChatbotManagerStore.getState() as any).resetStore();
            (LoadedChatbotStore.getState() as any).resetStore();
            (ViewStore.getState() as any).resetStore();
        } catch (error) {
            console.warn('Error clearing stores:', error);
        }
        
        localStorage.setItem('authToken', token);
        
        const newState = { 
            user: userData,
            isLoggedIn: true
        };
        
        set(newState);
        saveToStorage(newState);
        
        console.log('UserAuthStore state after login:', get());
    },

    logout: () => {
        console.log('UserAuthStore logout called');
        localStorage.removeItem('authToken');
        
        const newState = {
            user: null,
            isLoggedIn: false
        };
        
        set(newState);
        saveToStorage(newState);
        
        console.log('UserAuthStore state after logout:', get());
    }
}));

// Load persisted state when the store is created
const persistedState = loadFromStorage();
if (persistedState) {
    UserAuthStore.getState().loadPersistedState();
}

export default UserAuthStore;
