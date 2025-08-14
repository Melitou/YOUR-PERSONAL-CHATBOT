import { useEffect, ReactNode } from 'react';
import UserAuthStore from '../stores/UserAuthStore';

interface ProtectedRouteProps {
    children: ReactNode;
    requiredPermission?: string;
    requiredRole?: string;
    fallback?: ReactNode;
}

const ProtectedRoute = ({ 
    children, 
    requiredPermission, 
    requiredRole, 
    fallback = <div>Access Denied</div> 
}: ProtectedRouteProps) => {
    const { user, isLoggedIn, hasPermission, refreshUserData } = UserAuthStore();

    useEffect(() => {
        // Refresh user data to ensure we have latest permissions
        if (isLoggedIn) {
            refreshUserData();
        }
    }, [isLoggedIn, refreshUserData]);

    // Not logged in
    if (!isLoggedIn || !user) {
        return <div>Please log in to access this feature</div>;
    }

    // Check specific permission
    if (requiredPermission && !hasPermission(requiredPermission)) {
        return <>{fallback}</>;
    }

    // Check specific role
    if (requiredRole && user.role !== requiredRole) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
};

export default ProtectedRoute;