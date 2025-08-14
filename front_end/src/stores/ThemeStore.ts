import { create } from "zustand";

export type Theme = 'light' | 'dark';

interface ThemeState {
    theme: Theme;
    toggleTheme: () => void;
    setTheme: (theme: Theme) => void;
}

// Helper function to detect system preference
const getSystemPreference = (): Theme => {
    if (typeof window !== 'undefined' && window.matchMedia) {
        return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    return 'dark'; // Default to dark theme
};

// Helper function to get initial theme
const getInitialTheme = (): Theme => {
    const savedTheme = localStorage.getItem('userTheme') as Theme;
    if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
        return savedTheme;
    }
    return getSystemPreference();
};

const ThemeStore = create<ThemeState>((set, get) => ({
    theme: getInitialTheme(),

    toggleTheme: () => {
        const currentTheme = get().theme;
        const newTheme: Theme = currentTheme === 'light' ? 'dark' : 'light';
        localStorage.setItem('userTheme', newTheme);
        set({ theme: newTheme });
    },

    setTheme: (theme: Theme) => {
        localStorage.setItem('userTheme', theme);
        set({ theme });
    }
}));

export default ThemeStore;
