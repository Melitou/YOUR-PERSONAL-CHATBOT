import React, { useState } from 'react';
import { authApi } from '../utils/api';
import UserAuthStore from '../stores/UserAuthStore';
import ViewStore from '../stores/ViewStore';
import SignupPage from './SignupPage';

const AuthPage: React.FC = () => {
    const [isSignupMode, setIsSignupMode] = useState(false);
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');

    const { login } = UserAuthStore();
    const { addError } = ViewStore();

    // If in signup mode, render SignupPage
    if (isSignupMode) {
        return <SignupPage onSwitchToLogin={() => setIsSignupMode(false)} />;
    }

    const handleSubmit = async (e: React.FormEvent) => {
        console.log('handleSubmit');
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await authApi.login({ username, password });
            console.log('Login response:', response);

            // Ensure we have a token from the server (check for access_token)
            if (!response.access_token) {
                throw new Error('No authentication token received from server');
            }

            // Update the auth store with user data and token
            const userData = {
                name: (response.user.first_name?.trim() && response.user.last_name?.trim())
                    ? `${response.user.first_name.trim()} ${response.user.last_name.trim()}`
                    : response.user.user_name || username,
                role: response.user.role || 'User',
                email: response.user.email || username
            };
            console.log('Login userData:', userData);
            login(userData, response.access_token);

        } catch (err: any) {
            const errorMessage = err.message || 'Login failed. Please check your credentials.';
            console.error('Authentication failed:', errorMessage);
            setError(errorMessage);
            addError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
            {/* Animated background elements */}
            <div className="floating-element w-20 h-20 top-10 left-10" style={{ animationDelay: '0s' }}></div>
            <div className="floating-element w-32 h-32 top-1/4 right-10" style={{ animationDelay: '2s' }}></div>
            <div className="floating-element w-16 h-16 bottom-20 left-1/4" style={{ animationDelay: '4s' }}></div>
            <div className="glow-element w-40 h-40 top-1/3 left-1/3" style={{ animationDelay: '1s' }}></div>
            <div className="glow-element w-60 h-60 bottom-10 right-1/4" style={{ animationDelay: '3s' }}></div>

            <div className="glass-card w-full max-w-md p-8 relative z-10">
                <div className="text-center mb-8">
                    <div className="w-20 h-20 mx-auto mb-6 glass rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-4xl glass-text">
                            lock
                        </span>
                    </div>
                    <h1 className="text-3xl font-light glass-text mb-2">Welcome Back</h1>
                    <p className="glass-text opacity-80">Sign in to your personal AI assistant</p>
                </div>

                {error && (
                    <div className="glass-dark p-4 rounded-lg mb-6 border border-red-300/30">
                        <div className="flex items-center space-x-2">
                            <span className="material-symbols-outlined text-red-300 text-sm">
                                error
                            </span>
                            <p className="text-red-200 text-sm">{error}</p>
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Username
                        </label>
                        <input
                            type="text"
                            value={username}
                            onChange={(e) => setUsername(e.target.value)}
                            required
                            className="glass-input w-full px-4 py-3 glass-text placeholder-white/60 text-white"
                            placeholder="Enter your username"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Password
                        </label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            required
                            className="glass-input w-full px-4 py-3 glass-text placeholder-white/60 text-white"
                            placeholder="Enter your password"
                        />
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="glass-button w-full px-6 py-3 text-center font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                <span>Signing In...</span>
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-lg">
                                    login
                                </span>
                                <span>Sign In</span>
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <p className="glass-text opacity-70 text-sm">
                        Don't have an account?{' '}
                        <button
                            onClick={() => setIsSignupMode(true)}
                            className="glass-text hover:opacity-100 transition-opacity duration-200 underline cursor-pointer"
                        >
                            Sign up here
                        </button>
                    </p>
                </div>

                <div className="mt-8 text-center">
                    <p className="text-xs glass-text opacity-70">
                        Powered by AIbyDNA
                    </p>
                </div>
            </div>
        </div>
    );
};

export default AuthPage;