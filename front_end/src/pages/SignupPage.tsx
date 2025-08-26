import React, { useState } from 'react';
import { authApi } from '../utils/api';
import ViewStore from '../stores/ViewStore';

interface SignupPageProps {
    onSwitchToLogin: () => void;
}

const SignupPage: React.FC<SignupPageProps> = ({ onSwitchToLogin }) => {
    const [formData, setFormData] = useState({
        user_name: '',
        password: '',
        confirmPassword: '',
        first_name: '',
        last_name: '',
        email: '',
        role: 'User'
    });
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});

    const { addError, addSuccess } = ViewStore();

    const validateField = (name: string, value: string): string => {
        switch (name) {
            case 'user_name':
                if (value.length < 3) return 'Username must be at least 3 characters';
                if (value.length > 50) return 'Username must be less than 50 characters';
                return '';
            case 'password':
                if (value.length < 6) return 'Password must be at least 6 characters';
                return '';
            case 'confirmPassword':
                if (value !== formData.password) return 'Passwords do not match';
                return '';
            case 'first_name':
                if (value.length < 1) return 'First name is required';
                if (value.length > 50) return 'First name must be less than 50 characters';
                return '';
            case 'last_name':
                if (value.length < 1) return 'Last name is required';
                if (value.length > 50) return 'Last name must be less than 50 characters';
                return '';
            case 'email':
                const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailRegex.test(value)) return 'Please enter a valid email address';
                return '';
            default:
                return '';
        }
    };

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));

        // Clear field error when user starts typing
        if (fieldErrors[name]) {
            setFieldErrors(prev => ({ ...prev, [name]: '' }));
        }

        // Validate field in real-time
        const fieldError = validateField(name, value);
        if (fieldError) {
            setFieldErrors(prev => ({ ...prev, [name]: fieldError }));
        }
    };

    const validateForm = (): boolean => {
        const errors: Record<string, string> = {};

        Object.keys(formData).forEach(key => {
            if (key !== 'confirmPassword') {
                const error = validateField(key, formData[key as keyof typeof formData]);
                if (error) errors[key] = error;
            }
        });

        // Check confirm password
        const confirmPasswordError = validateField('confirmPassword', formData.confirmPassword);
        if (confirmPasswordError) errors.confirmPassword = confirmPasswordError;

        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');

        if (!validateForm()) {
            setError('Please fix the errors above');
            return;
        }

        setLoading(true);

        try {
            const { confirmPassword, ...signupData } = formData;
            const response = await authApi.signup(signupData);

            console.log('Signup response:', response);
            setSuccess(true);
            addSuccess('Account created successfully! Please log in with your credentials.');

            // After 2 seconds, switch to login
            setTimeout(() => {
                onSwitchToLogin();
            }, 2000);

        } catch (err: any) {
            const errorMessage = err.message || 'Registration failed. Please try again.';
            console.error('Signup failed:', errorMessage);
            setError(errorMessage);
            addError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden">
                {/* Animated background elements */}
                <div className="floating-element w-20 h-20 top-10 left-10" style={{ animationDelay: '0s' }}></div>
                <div className="floating-element w-32 h-32 top-1/4 right-10" style={{ animationDelay: '2s' }}></div>
                <div className="floating-element w-16 h-16 bottom-20 left-1/4" style={{ animationDelay: '4s' }}></div>
                <div className="glow-element w-40 h-40 top-1/3 left-1/3" style={{ animationDelay: '1s' }}></div>
                <div className="glow-element w-60 h-60 bottom-10 right-1/4" style={{ animationDelay: '3s' }}></div>

                <div className="glass-card w-full max-w-sm p-6 relative z-10 text-center">
                    <div className="w-16 h-16 mx-auto mb-6 glass rounded-full flex items-center justify-center">
                        <span className="material-symbols-outlined text-4xl glass-text text-green-400">
                            check_circle
                        </span>
                    </div>
                    <h1 className="text-3xl font-light glass-text mb-2">Account Created!</h1>
                    <p className="glass-text opacity-80 mb-4">Your account has been successfully created.</p>
                    <p className="glass-text opacity-60 text-sm">Redirecting to login...</p>
                </div>
            </div>
        );
    }

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

                    <h1 className="text-3xl font-light glass-text mb-2">Create Account</h1>
                    <p className="glass-text opacity-80">Join your personal AI assistant</p>
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

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="block text-sm font-medium glass-text mb-2">
                                First Name
                            </label>
                            <input
                                type="text"
                                name="first_name"
                                value={formData.first_name}
                                onChange={handleInputChange}
                                required
                                className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                                placeholder="First name"
                            />
                            {fieldErrors.first_name && (
                                <p className="text-red-300 text-xs mt-1">{fieldErrors.first_name}</p>
                            )}
                        </div>

                        <div>
                            <label className="block text-sm font-medium glass-text mb-2">
                                Last Name
                            </label>
                            <input
                                type="text"
                                name="last_name"
                                value={formData.last_name}
                                onChange={handleInputChange}
                                required
                                className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                                placeholder="Last name"
                            />
                            {fieldErrors.last_name && (
                                <p className="text-red-300 text-xs mt-1">{fieldErrors.last_name}</p>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Username
                        </label>
                        <input
                            type="text"
                            name="user_name"
                            value={formData.user_name}
                            onChange={handleInputChange}
                            required
                            className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                            placeholder="Choose a username"
                        />
                        {fieldErrors.user_name && (
                            <p className="text-red-300 text-xs mt-1">{fieldErrors.user_name}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Email
                        </label>
                        <input
                            type="email"
                            name="email"
                            value={formData.email}
                            onChange={handleInputChange}
                            required
                            className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                            placeholder="Enter your email"
                        />
                        {fieldErrors.email && (
                            <p className="text-red-300 text-xs mt-1">{fieldErrors.email}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Role
                        </label>
                        <select
                            name="role"
                            value={formData.role}
                            onChange={handleInputChange}
                            required
                            className="glass-input w-full px-3 py-2 glass-text text-white rounded-full"
                        >
                            <option value="User" className="bg-[#474f47] text-white">User</option>
                            <option value="Super User" className="bg-[#474f47] text-white">Super User</option>
                            <option value="Client" className="bg-[#474f47] text-white">Client</option>
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Password
                        </label>
                        <input
                            type="password"
                            name="password"
                            value={formData.password}
                            onChange={handleInputChange}
                            required
                            className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                            placeholder="Create a password"
                        />
                        {fieldErrors.password && (
                            <p className="text-red-300 text-xs mt-1">{fieldErrors.password}</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium glass-text mb-2">
                            Confirm Password
                        </label>
                        <input
                            type="password"
                            name="confirmPassword"
                            value={formData.confirmPassword}
                            onChange={handleInputChange}
                            required
                            className="glass-input w-full px-3 py-2 glass-text placeholder-white/60 text-white"
                            placeholder="Confirm your password"
                        />
                        {fieldErrors.confirmPassword && (
                            <p className="text-red-300 text-xs mt-1">{fieldErrors.confirmPassword}</p>
                        )}
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="glass-button w-full px-4 py-2 text-center font-medium transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                    >
                        {loading ? (
                            <>
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                                <span>Creating Account...</span>
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined text-lg cursor-pointer">
                                    person_add
                                </span>
                                <span>Create Account</span>
                            </>
                        )}
                    </button>
                </form>

                <div className="mt-6 text-center">
                    <p className="glass-text opacity-70 text-sm">
                        Already have an account?{' '}
                        <button
                            onClick={onSwitchToLogin}
                            className="glass-text hover:opacity-100 transition-opacity duration-200 underline cursor-pointer"
                        >
                            Sign in here
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

export default SignupPage;
