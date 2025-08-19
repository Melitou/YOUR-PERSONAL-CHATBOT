import { useState } from 'react';
import { Avatar, Menu, MenuItem, IconButton } from '@mui/material';
import { FaUser, FaBars } from 'react-icons/fa';
import UserAuthStore from '../stores/UserAuthStore';
import ViewStore from '../stores/ViewStore';
import ThemeStore from '../stores/ThemeStore';
import { authApi } from '../utils/api';

const HeaderComponent = () => {
    const { user, logout } = UserAuthStore();
    const { sidebarOpen, setSidebarOpen, navigateToHome } = ViewStore();
    const { theme, toggleTheme } = ThemeStore();
    const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
    const isMenuOpen = Boolean(menuAnchorEl);


    const handleLogout = async () => {
        try {
            await authApi.logout();
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            // Clear local storage and update store regardless of API call result
            localStorage.removeItem('authToken');
            logout();
        }
    };

    return (
        <header className="px-2 sm:px-4 py-4 flex items-center border-b border-white/20 glass flex-shrink-0">
            <div className="flex items-center gap-2 w-full justify-between">
                {/* Sidebar Toggle Button and Title */}
                <div className="flex items-center gap-3">
                    <button
                        onClick={() => setSidebarOpen(!sidebarOpen)}
                        className="p-2 rounded-md hover:glass-light transition-colors glass-text"
                        aria-label="Toggle sidebar"
                    >
                        <FaBars size={20} />
                    </button>
                    <h1
                        className="text-lg sm:text-xl md:text-2xl glass-text font-light cursor-pointer hover:opacity-80 transition-opacity"
                        onClick={navigateToHome}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                navigateToHome();
                            }
                        }}
                        aria-label="Navigate to home page"
                        title="Go to home page"
                    >
                        Your Personal Chatbot
                    </h1>
                </div>

                {user && (
                    <div className="flex items-center gap-3 min-w-0 mr-4">
                        {/* Theme Toggle Button */}
                        <button
                            onClick={toggleTheme}
                            className="p-2 rounded-md hover:glass-light transition-colors glass-text text-xl"
                            aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
                            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
                        >
                            {theme === 'light' ? '🌙' : '☀️'}
                        </button>

                        {/* Logout Button - More Visible */}

                        <div className="flex items-center gap-2 min-w-0">
                            <IconButton
                                onClick={(e) => setMenuAnchorEl(e.currentTarget)}
                                size="small"
                                sx={{ p: 0 }}
                                aria-controls={isMenuOpen ? 'user-menu' : undefined}
                                aria-haspopup="true"
                                aria-expanded={isMenuOpen ? 'true' : undefined}
                            >
                                <Avatar
                                    sx={{ width: 28, height: 28, bgcolor: 'primary.main', backgroundColor: 'black', color: 'white' }}
                                >
                                    <FaUser className="text-xs sm:text-sm" />
                                </Avatar>
                            </IconButton>
                            <div className="flex flex-col text-[11px] sm:text-sm leading-tight min-w-0 max-w-[40vw] sm:max-w-none">
                                <div className="font-medium glass-text truncate">{user.name}</div>
                                <div className="text-[10px] sm:text-xs glass-text opacity-70 truncate">{user.role}</div>
                            </div>
                        </div>
                        <Menu
                            id="user-menu"
                            anchorEl={menuAnchorEl}
                            open={isMenuOpen}
                            onClose={() => setMenuAnchorEl(null)}
                            anchorOrigin={{ vertical: 35, horizontal: 'left' }}
                            transformOrigin={{ vertical: 'top', horizontal: 'left' }}
                            keepMounted
                        >
                            <MenuItem
                                onClick={() => {
                                    setMenuAnchorEl(null);
                                    handleLogout();
                                }}
                                className="flex items-center gap-2"
                            >
                                <span className="material-symbols-outlined text-sm">
                                    logout
                                </span>
                                Logout
                            </MenuItem>
                        </Menu>
                    </div>
                )}
            </div>
        </header>
    )
}

export default HeaderComponent;