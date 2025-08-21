import { useEffect } from 'react'
import './App.css'
import MainPage from './pages/MainPage'
import AuthPage from './pages/AuthPage'
import ClientDashboard from './pages/ClientDashboard'
import UserAuthStore from './stores/UserAuthStore'
import ThemeStore from './stores/ThemeStore'
import { authApi } from './utils/api'
import ErrorComponent from './components/ErrorComponent'
import ViewStore from './stores/ViewStore'

function App() {
  const { isLoggedIn, login, logout, user } = UserAuthStore();
  const { addError } = ViewStore();
  const { theme } = ThemeStore();

  // Apply theme class to document body
  useEffect(() => {
    document.body.className = `${theme}-theme`;
  }, [theme]);

  useEffect(() => {
    // Check if user is already authenticated on app load
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const response = await authApi.getCurrentUser();
          console.log('getCurrentUser response:', response);
          // Format user data consistently with login process
          const userData = {
            name: (response.first_name?.trim() && response.last_name?.trim())
              ? `${response.first_name.trim()} ${response.last_name.trim()}`
              : response.user_name || 'User',
            role: response.role || 'User',
            email: response.email || 'user@example.com'
          };
          console.log('Formatted userData:', userData);
          login(userData, token);
        } catch (error) {
          // Token is invalid, remove it
          console.error('Authentication check failed:', error);
          addError('Session expired - please log in again');
          logout();
        }
      }
    };

    checkAuth();
  }, [login, logout]);

  const renderMainContent = () => {
    if (!isLoggedIn) {
      return <AuthPage />;
    }

    // Role-based routing
    if (user?.role === 'Client') {
      return <ClientDashboard />;
    } else {
      // Users and Super Users see the MainPage
      return <MainPage />;
    }
  };

  return (
    <div>
      {renderMainContent()}
      <ErrorComponent />
    </div>
  )
}

export default App