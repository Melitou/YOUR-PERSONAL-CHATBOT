import { create } from "zustand";

const UserAuthStore = create((set) => ({
    user: {
        name: "Test User",
        role: "Super User"
    },
    isLoggedIn: false,

    login: (userData: any) => set({ 
        user: userData,
        isLoggedIn: true
    }),

    logout: () => set({
        user: null,
        isLoggedIn: false
    }),

    setRole: (role: string) => set((state: any) => ({
        user: state.user ? { ...state.user, role } : null
    }))
}));

export default UserAuthStore;
