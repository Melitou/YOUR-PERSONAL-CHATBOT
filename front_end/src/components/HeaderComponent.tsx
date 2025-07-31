import { Button, Avatar, Tooltip } from '@mui/material';
import { FaSignOutAlt, FaUser } from 'react-icons/fa';
import UserAuthStore from '../stores/UserAuthStore';
import { authApi } from '../utils/api';

const HeaderComponent = () => {
    const { user, logout } = UserAuthStore() as any;

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
        <header className="px-4 py-2 flex items-center border-b border-gray-200 bg-white flex-shrink-0">
            <div className="flex items-center gap-2 w-full justify-between">
                <h1 className="text-xl text-black font-light">YourPersonalChatBot</h1>
                
                {user && (
                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2">
                            <Avatar 
                                sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}
                            >
                                <FaUser className="text-sm" />
                            </Avatar>
                            <div className="text-sm">
                                <div className="font-medium text-gray-800">{user.name}</div>
                                <div className="text-xs text-gray-500">{user.role}</div>
                            </div>
                        </div>
                        
                        <Tooltip title="Logout">
                            <Button
                                onClick={handleLogout}
                                variant="outlined"
                                size="small"
                                startIcon={<FaSignOutAlt />}
                                sx={{
                                    textTransform: 'none',
                                    borderRadius: 2,
                                    minWidth: 'auto',
                                    px: 2
                                }}
                            >
                                Logout
                            </Button>
                        </Tooltip>
                    </div>
                )}
            </div>
        </header>
    )
}

export default HeaderComponent;