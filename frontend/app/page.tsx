"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

/**
 * Root route (`/`) — previously missing entirely, meaning the base URL
 * 404'd (a real gap: anyone visiting http://localhost:3000/ directly, or
 * a load balancer health check hitting `/`, would fail). Redirects to the
 * dashboard if logged in, or the login page otherwise.
 */
export default function RootPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    router.replace(user ? "/dashboard" : "/login");
  }, [user, loading, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950">
      <Loader2 className="animate-spin text-slate-500" size={24} />
    </div>
  );
}
