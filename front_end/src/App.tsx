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
    // Load persisted state first
    const { loadPersistedState } = UserAuthStore.getState();
    loadPersistedState();
    
    // Check if user is already authenticated on app load
    const checkAuth = async () => {
      const token = localStorage.getItem('authToken');
      if (token) {
        try {
          const userData = await authApi.getCurrentUser();
          // Update user data in case it changed on the backend
          login(userData, token);
        } catch (error) {
          // Token is invalid, remove it and clear persisted state
          console.error('Authentication check failed:', error);
          addError('Session expired - please log in again');
          logout();
        }
      } else if (isLoggedIn) {
        // Token is missing but user is marked as logged in (persisted state issue)
        logout();
      }
    };

    checkAuth();
  }, [login, logout, isLoggedIn]);

  return (
    <div>
      {isLoggedIn ? <MainPage /> : <AuthPage />}
      <ErrorComponent />
    </div>
  )
}

export default App