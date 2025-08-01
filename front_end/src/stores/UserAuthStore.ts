import { create } from "zustand";

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
}

const UserAuthStore = create<UserAuthState>((set) => ({
    user: null,
    isLoggedIn: false,

    login: (userData: User, token: string) => {
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
