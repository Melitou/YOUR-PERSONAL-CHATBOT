import { useEffect } from 'react'
import './App.css'
import MainPage from './pages/MainPage'
import AuthPage from './pages/AuthPage'
import UserAuthStore from './stores/UserAuthStore'
import { authApi } from './utils/api'
import ErrorComponent from './components/ErrorComponent'
import ViewStore from './stores/ViewStore'

function App() {
  const { isLoggedIn, login, logout } = UserAuthStore();
  const { addError } = ViewStore();

  useEffect(() => {
    // Check if user is already authenticated on app load
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const userData = await authApi.getCurrentUser();
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