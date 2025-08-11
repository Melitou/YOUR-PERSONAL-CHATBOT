import { useState } from 'react';
import { Avatar, Menu, MenuItem, IconButton } from '@mui/material';
import { FaUser } from 'react-icons/fa';
import UserAuthStore from '../stores/UserAuthStore';
import { authApi } from '../utils/api';

const HeaderComponent = () => {
    const { user, logout } = UserAuthStore() as any;
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
        <header className="px-2 sm:px-4 py-4 flex items-center border-b border-gray-200 bg-white flex-shrink-0">
            <div className="flex items-center gap-2 w-full justify-end sm:justify-between">
                <h1 className="hidden sm:block text-lg sm:text-xl md:text-2xl text-black font-light">YourPersonalChatBot</h1>
                
                {user && (
                    <div className="flex items-center gap-3 min-w-0">
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
                                <div className="font-medium text-gray-800 truncate">{user.name}</div>
                                <div className="text-[10px] sm:text-xs text-gray-500 truncate">{user.role}</div>
                            </div>
                        </div>
                        <Menu
                            id="user-menu"
                            anchorEl={menuAnchorEl}
                            open={isMenuOpen}
                            onClose={() => setMenuAnchorEl(null)}
                            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
                            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
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