import { type ReactNode } from 'react';
import UserAuthStore from '../stores/UserAuthStore';

interface ProtectedRouteProps {
    children: ReactNode;
    requiredRole?: 'User' | 'Super User' | 'Client';
    allowedRoles?: ('User' | 'Super User' | 'Client')[];
    fallback?: ReactNode;
}

const ProtectedRoute = ({
    children,
    requiredRole,
    allowedRoles,
    fallback = <div>Access Denied</div>
}: ProtectedRouteProps) => {
    const { user, isLoggedIn } = UserAuthStore();

    // Not logged in
    if (!isLoggedIn || !user) {
        return <div>Please log in to access this feature</div>;
    }

    // Check specific role
    if (requiredRole && user.role !== requiredRole) {
        return <>{fallback}</>;
    }

    // Check allowed roles
    if (allowedRoles && !allowedRoles.includes(user.role as any)) {
        return <>{fallback}</>;
    }

    return <>{children}</>;
};

export default ProtectedRoute;