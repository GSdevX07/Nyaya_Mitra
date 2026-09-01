import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth, type Role } from "../lib/auth";
import { ShieldAlert } from "lucide-react";

interface ProtectedRouteProps {
  allowedRoles?: Role[];
  children?: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ allowedRoles, children }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-wider">
            Verifying Credentials...
          </p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (allowedRoles && allowedRoles.length > 0 && user.role !== "PLATFORM_ADMIN") {
    if (!allowedRoles.includes(user.role)) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-background p-6">
          <div className="max-w-md w-full bg-card border-2 border-destructive/40 p-8 rounded-sm text-center space-y-4 shadow-lg">
            <div className="w-12 h-12 rounded-full bg-destructive/10 text-destructive flex items-center justify-center mx-auto">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="text-xl font-serif font-black text-foreground uppercase tracking-wide">
              Access Restricted
            </h2>
            <p className="text-sm text-muted-foreground font-sans">
              Your role <span className="font-mono font-bold text-foreground">[{user.role}]</span> does not have
              clearance to access this operational module.
            </p>
            <div className="pt-4 border-t border-border">
              <button
                onClick={() => window.history.back()}
                className="w-full bg-primary text-primary-foreground font-mono text-xs uppercase font-bold py-2.5 rounded-sm hover:opacity-90 transition-opacity"
              >
                Return to Authorized Area
              </button>
            </div>
          </div>
        </div>
      );
    }
  }

  return children ? <>{children}</> : <Outlet />;
};
