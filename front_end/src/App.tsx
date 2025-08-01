import { useEffect } from 'react'
import './App.css'
import MainPage from './pages/MainPage'
import AuthPage from './pages/AuthPage'
import UserAuthStore from './stores/UserAuthStore'
import { authApi } from './utils/api'

function App() {
  const { isLoggedIn, login, logout } = UserAuthStore();

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
          logout();
        }
      }
    };

    checkAuth();
  }, [login, logout]);

  return (
    <div>
      {isLoggedIn ? <MainPage /> : <AuthPage />}
    </div>
  )
}

export default App