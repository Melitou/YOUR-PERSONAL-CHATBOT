import { create } from "zustand";
import ChatbotManagerStore from "./ChatbotManagerStore";
import LoadedChatbotStore from "./LoadedChatbotStore";
import ViewStore from "./ViewStore";

interface User {
    name: string;
    email?: string;
    role?: 'User' | 'Super User' | 'Client';
}

interface UserAuthState {
    user: User | null;
    isLoggedIn: boolean;
    login: (userData: User, token: string) => void;
    logout: () => void;
}

const UserAuthStore = create<UserAuthState>((set) => ({
    user: null,
    isLoggedIn: false,

    login: (userData: User, token: string) => {
        // Clear all stores when user logs in
        (ChatbotManagerStore.getState() as any).resetStore();
        (LoadedChatbotStore.getState() as any).resetStore();
        (ViewStore.getState() as any).resetStore();

        localStorage.setItem('authToken', token);
        set({
            user: userData,
            isLoggedIn: true
        });
    },

    logout: () => {
        localStorage.removeItem('authToken');
        set({
            user: null,
            isLoggedIn: false
        });
    }
}));

export default UserAuthStore;
