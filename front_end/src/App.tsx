import { useEffect } from 'react'
import './App.css'
import MainPage from './pages/MainPage'
import AuthPage from './pages/AuthPage'
import UserAuthStore from './stores/UserAuthStore'
import ThemeStore from './stores/ThemeStore'
import { authApi } from './utils/api'
import ErrorComponent from './components/ErrorComponent'
import ViewStore from './stores/ViewStore'

function App() {
  const { isLoggedIn, login, logout } = UserAuthStore();
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
          // Format user data consistently with login process
          const userData = {
            name: `${response.first_name} ${response.last_name}` || response.user_name || 'User',
            role: response.role || 'User',
            email: response.email || 'user@example.com'
          };
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

  return (
    <div>
      {isLoggedIn ? <MainPage /> : <AuthPage />}
      <ErrorComponent />
    </div>
  )
}

export default App