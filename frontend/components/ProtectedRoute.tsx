"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactNode;
  /** Roles allowed to view this page. Omit to allow any authenticated user. */
  allowedRoles?: string[];
  /** Where to send a user whose role isn't allowed (default: /dashboard). */
  redirectOnRoleDenied?: string;
}

/**
 * Client-side auth gate — mirrors the backend's JWT + RBAC enforcement
 * (api/auth/jwt_handler.py) so unauthenticated or under-privileged users
 * never see a broken/empty page while their API calls silently 401/403.
 * The backend remains the actual security boundary; this is UX, not defense.
 */
export function ProtectedRoute({ children, allowedRoles, redirectOnRoleDenied = "/dashboard" }: ProtectedRouteProps) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;

    if (!user) {
      router.replace("/login");
      return;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
      router.replace(redirectOnRoleDenied);
    }
  }, [user, loading, allowedRoles, redirectOnRoleDenied, router]);

  const isAuthorized = user && (!allowedRoles || allowedRoles.includes(user.role));

  if (loading || !isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-950">
        <Loader2 className="animate-spin text-slate-500" size={24} />
      </div>
    );
  }

  return <>{children}</>;
}
