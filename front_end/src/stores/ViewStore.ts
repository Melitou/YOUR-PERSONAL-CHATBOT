import { create } from "zustand";

// To manage UI related states

const ViewStore = create((set) => ({
    
    sidebarOpen: false,
    setSidebarOpen: (sidebarOpen: boolean) => set({ sidebarOpen }),

}));

export default ViewStore;