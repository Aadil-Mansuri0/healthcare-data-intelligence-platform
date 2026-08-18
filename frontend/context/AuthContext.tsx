"use client";

import { createContext, useContext, useState, useEffect, ReactNode, useRef } from "react";
import axios from "axios";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  username: string;
  email: string;
  full_name: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// ─── Module-level refresh state ────────────────────────────────────────────
// Lives outside the component so the axios interceptor (registered once,
// see useEffect below) can share it across every request in flight, and so
// concurrent 401s from multiple simultaneous API calls don't each trigger
// their own /api/auth/refresh call — they queue behind a single in-flight
// refresh instead (the classic "thundering herd on token expiry" bug).
let isRefreshing = false;
let refreshQueue: Array<(token: string | null) => void> = [];

function subscribeToRefresh(callback: (token: string | null) => void) {
  refreshQueue.push(callback);
}

function notifyRefreshSubscribers(token: string | null) {
  refreshQueue.forEach((cb) => cb(token));
  refreshQueue = [];
}

async function performTokenRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem("refresh_token");
  if (!refreshToken) return null;

  try {
    const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    });
    const newAccessToken = response.data.access_token;
    localStorage.setItem("access_token", newAccessToken);
    axios.defaults.headers.common["Authorization"] = `Bearer ${newAccessToken}`;
    return newAccessToken;
  } catch {
    // Refresh token itself expired/invalid (e.g. > 7 days idle, or revoked)
    // — nothing left to do but force a real re-login.
    return null;
  }
}

function forceLogoutRedirect() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
  delete axios.defaults.headers.common["Authorization"];
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const interceptorRegistered = useRef(false);

  useEffect(() => {
    const storedToken = localStorage.getItem("access_token");
    const storedUser = localStorage.getItem("user");
    if (storedToken && storedUser) {
      setToken(storedToken);
      setUser(JSON.parse(storedUser));
      axios.defaults.headers.common["Authorization"] = `Bearer ${storedToken}`;
    }
    setLoading(false);
  }, []);

  // Registers the 401 → auto-refresh → retry interceptor exactly once per
  // app lifetime (not per-render) — this is what was previously entirely
  // missing: /api/auth/refresh existed on the backend but nothing on the
  // frontend ever called it, so every session silently broke ~30 minutes
  // after login (the access token's expiry) with no recovery.
  useEffect(() => {
    if (interceptorRegistered.current) return;
    interceptorRegistered.current = true;

    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Only handle 401s, only retry once per request (avoids infinite
        // loops if the refreshed token is somehow still rejected), and
        // never intercept the refresh call itself failing.
        if (
          error.response?.status !== 401 ||
          originalRequest._retry ||
          originalRequest.url?.includes("/api/auth/refresh") ||
          originalRequest.url?.includes("/api/auth/login")
        ) {
          return Promise.reject(error);
        }

        originalRequest._retry = true;

        if (isRefreshing) {
          // A refresh is already in flight (triggered by a different
          // concurrent request) — queue this request to retry once it
          // resolves, instead of firing a second redundant refresh call.
          return new Promise((resolve, reject) => {
            subscribeToRefresh((newToken) => {
              if (newToken) {
                originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
                resolve(axios(originalRequest));
              } else {
                reject(error);
              }
            });
          });
        }

        isRefreshing = true;
        const newToken = await performTokenRefresh();
        isRefreshing = false;
        notifyRefreshSubscribers(newToken);

        if (newToken) {
          originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
          return axios(originalRequest);
        }

        // Refresh token also invalid/expired — this is a real session end,
        // not a transient error. Force logout + redirect rather than
        // leaving the user staring at silent 401s.
        forceLogoutRedirect();
        return Promise.reject(error);
      }
    );

    return () => {
      axios.interceptors.response.eject(interceptorId);
    };
  }, []);

  const login = async (username: string, password: string) => {
    const params = new URLSearchParams();
    params.append("username", username);
    params.append("password", password);

    const response = await axios.post(`${API_BASE_URL}/api/auth/login`, params, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });

    const { access_token, refresh_token, user: userData } = response.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(userData));
    axios.defaults.headers.common["Authorization"] = `Bearer ${access_token}`;

    setToken(access_token);
    setUser(userData);
  };

  const logout = () => {
    // Revoke server-side first (best-effort — see api/auth/token_blacklist.py)
    // so a captured/leaked token can't be replayed after logout, not just
    // discarded client-side.
    axios.post(`${API_BASE_URL}/api/auth/logout`).catch(() => {
      // Non-fatal — client-side token discard below still happens regardless
    });

    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    delete axios.defaults.headers.common["Authorization"];
    setToken(null);
    setUser(null);
  };

  const hasRole = (roles: string[]) => !!user && roles.includes(user.role);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, hasRole }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
