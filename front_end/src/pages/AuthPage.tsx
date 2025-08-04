import React, { useState } from 'react';
import { Alert, Button, TextField, Paper, Typography } from '@mui/material';
import { authApi } from '../utils/api';
import UserAuthStore from '../stores/UserAuthStore';
import ViewStore from '../stores/ViewStore';

const AuthPage: React.FC = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const { login } = UserAuthStore();
    const { addError } = ViewStore();

    const handleSubmit = async (e: React.FormEvent) => {
        console.log('handleSubmit');
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await authApi.login({ username, password });
            
            // Ensure we have a token from the server (check for access_token)
            if (!response.access_token) {
                throw new Error('No authentication token received from server');
            }
            
            // Update the auth store with user data and token
            login({
                name: `${response.user.first_name} ${response.user.last_name}` || response.user.user_name || username,
                role: response.user.role || 'User',
                email: response.user.email || username
            }, response.access_token);
            
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
        <div className="min-h-screen flex items-center justify-center bg-gray-100 p-4">
            <Paper elevation={3} className="w-full max-w-md p-6">
                <Typography variant="h4" component="h1" className="text-center mb-6">
                    Login
                </Typography>

                {error && (
                    <Alert severity="error" className="mb-4">
                        {error}
                    </Alert>
                )}

                <form onSubmit={handleSubmit}>
                    <TextField
                        fullWidth
                        label="Username"
                        type="text"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        required
                        margin="normal"
                    />

                    <TextField
                        fullWidth
                        label="Password"
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        margin="normal"
                    />

                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        size="large"
                        disabled={loading}
                        sx={{ mt: 3, mb: 2 }}
                    >
                        {loading ? 'Signing In...' : 'Sign In'}
                    </Button>
                </form>
            </Paper>
        </div>
    );
};

export default AuthPage;