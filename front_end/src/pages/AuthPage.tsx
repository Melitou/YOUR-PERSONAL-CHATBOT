import React, { useState } from 'react';
import { Alert, Button, TextField, Paper, Typography, Box, IconButton, InputAdornment } from '@mui/material';
import { Visibility, VisibilityOff, Login as LoginIcon, Person, Lock } from '@mui/icons-material';
import { authApi } from '../utils/api';
import UserAuthStore from '../stores/UserAuthStore';

const AuthPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    
    const { login } = UserAuthStore() as any;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setLoading(true);

        try {
            const response = await authApi.login({ email, password });
            
            // Store the token if provided
            if (response.token) {
                localStorage.setItem('authToken', response.token);
            }
            
            // Update the auth store with user data
            login({
                name: response.user?.name || response.name || email,
                role: response.user?.role || response.role || 'User',
                email: response.user?.email || response.email || email
            });
            
        } catch (err: any) {
            setError(err.message || 'Login failed. Please check your credentials.');
        } finally {
            setLoading(false);
        }
    };

    const handleClickShowPassword = () => {
        setShowPassword(!showPassword);
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br to-indigo-100 p-4">
            <Paper 
                elevation={10} 
                className="w-full max-w-md p-8 bg-white/95 backdrop-blur-sm"
                sx={{ 
                    borderRadius: 3,
                    boxShadow: '0 20px 40px rgba(0,0,0,0.1)'
                }}
            >
                <Box className="text-center mb-8">
                    <div className="mb-4 flex justify-center">
                        <div className="p-3 bg-black rounded-full">
                            <LoginIcon sx={{ fontSize: 32, color: 'white' }} />
                        </div>
                    </div>
                    <Typography 
                        variant="h4" 
                        component="h1" 
                        className="font-bold text-gray-800 mb-2"
                        sx={{ fontFamily: 'Montserrat' }}
                    >
                        Welcome Back
                    </Typography>
                    <Typography 
                        variant="body1" 
                        className="text-gray-600"
                        sx={{ fontFamily: 'Open Sans' }}
                    >
                        Sign in to access your personal chatbot
                    </Typography>
                </Box>

                {error && (
                    <Alert 
                        severity="error" 
                        className="mb-6"
                        sx={{ borderRadius: 2 }}
                    >
                        {error}
                    </Alert>
                )}

                <form onSubmit={handleSubmit} className="space-y-6">
                    <TextField
                        fullWidth
                        label="Email or Username"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        variant="outlined"
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <Person sx={{ color: 'text.secondary' }} />
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                borderRadius: 2,
                                '&:hover fieldset': {
                                    borderColor: 'primary.main',
                                },
                            },
                            mb: 4
                        }}
                    />

                    <TextField
                        fullWidth
                        label="Password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                        variant="outlined"
                        InputProps={{
                            startAdornment: (
                                <InputAdornment position="start">
                                    <Lock sx={{ color: 'text.secondary' }} />
                                </InputAdornment>
                            ),
                            endAdornment: (
                                <InputAdornment position="end">
                                    <IconButton
                                        aria-label="toggle password visibility"
                                        onClick={handleClickShowPassword}
                                        edge="end"
                                    >
                                        {showPassword ? <VisibilityOff /> : <Visibility />}
                                    </IconButton>
                                </InputAdornment>
                            ),
                        }}
                        sx={{
                            '& .MuiOutlinedInput-root': {
                                borderRadius: 2,
                                '&:hover fieldset': {
                                    borderColor: 'primary.main',
                                },
                            },
                        }}
                    />

                    <Button
                        type="submit"
                        fullWidth
                        variant="contained"
                        size="large"
                        disabled={loading}
                        sx={{
                            mt: 3,
                            mb: 2,
                            py: 1.5,
                            borderRadius: 2,
                            textTransform: 'none',
                            fontSize: '1.1rem',
                            fontWeight: 600,
                            background: 'linear-gradient(45deg, #000000 30%, #424242 90%)',
                            boxShadow: '0 3px 5px 2px rgba(66, 66, 66, .3)',
                            '&:hover': {
                                background: 'linear-gradient(45deg, #212121 30%, #616161 90%)',
                                boxShadow: '0 6px 10px 2px rgba(66, 66, 66, .3)',
                            },
                            '&:disabled': {
                                background: 'rgba(0,0,0,0.12)',
                                boxShadow: 'none',
                            }
                        }}
                    >
                        {loading ? 'Signing In...' : 'Sign In'}
                    </Button>
                </form>

                <Box className="mt-6 text-center">
                    <Typography 
                        variant="body2" 
                        className="text-gray-500"
                        sx={{ fontFamily: 'Open Sans' }}
                    >
                        Don't have an account? Contact your administrator
                    </Typography>
                </Box>
            </Paper>
        </div>
    );
};

export default AuthPage;
