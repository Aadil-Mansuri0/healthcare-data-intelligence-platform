"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../context/AuthContext";
import { Lock, User, ShieldCheck, Sparkles, Database, ArrowRight, Loader2 } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("Admin@123");
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async (u: string, p: string) => {
    setLoading(true);
    await login(u, p);
    router.push("/dashboard");
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleLogin(username, password);
  };

  const handleQuickLogin = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
    handleLogin(u, p);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Ambient background glows */}
      <div className="absolute -top-40 -left-40 w-96 h-96 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10 space-y-6">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-sky-400 via-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 font-black text-2xl mx-auto shadow-2xl shadow-sky-500/20 glow-sky">
            🏥
          </div>
          <h1 className="text-2xl font-black text-white tracking-tight">
            HealthData <span className="text-sky-400">IQ</span>
          </h1>
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Enterprise Healthcare Data Intelligence & Surveillance Platform (Medicare Part D)
          </p>
        </div>

        {/* Login Form Panel */}
        <div className="glass-panel rounded-2xl p-7 border border-slate-800 space-y-5 shadow-2xl">
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <span className="text-xs font-bold text-white uppercase tracking-wider">Enterprise Sign In</span>
            <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
              Instant Live Access
            </span>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4 text-xs">
            <div>
              <label className="text-slate-300 font-medium mb-1.5 block">Username / Principal</label>
              <div className="relative">
                <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2.5 text-white outline-none focus:border-sky-500 font-medium transition-colors"
                  placeholder="e.g. admin"
                  required
                />
              </div>
            </div>

            <div>
              <label className="text-slate-300 font-medium mb-1.5 block">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500" size={15} />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3.5 py-2.5 text-white outline-none focus:border-sky-500 font-medium transition-colors"
                  placeholder="••••••••"
                  required
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white font-bold rounded-xl py-2.5 transition-colors flex items-center justify-center gap-2 shadow-lg shadow-sky-600/20"
            >
              {loading ? (
                <>
                  <Loader2 size={15} className="animate-spin" /> Entering Dashboard...
                </>
              ) : (
                <>
                  Access Platform <ArrowRight size={15} />
                </>
              )}
            </button>
          </form>

          {/* 1-Click Instant Demo Accounts */}
          <div className="pt-3 border-t border-slate-800 space-y-2">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block text-center">
              1-Click Instant Login (Select Role)
            </span>
            <div className="grid grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => handleQuickLogin("admin", "Admin@123")}
                className="p-2.5 rounded-lg bg-slate-950 hover:bg-purple-950/40 border border-slate-800 hover:border-purple-500/50 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-purple-400 block group-hover:text-purple-300">Admin</span>
                <span className="text-[9px] text-slate-400 block truncate">Full System</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("analyst", "Analyst@123")}
                className="p-2.5 rounded-lg bg-slate-950 hover:bg-sky-950/40 border border-slate-800 hover:border-sky-500/50 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-sky-400 block group-hover:text-sky-300">Analyst</span>
                <span className="text-[9px] text-slate-400 block truncate">AI & Reports</span>
              </button>
              <button
                type="button"
                onClick={() => handleQuickLogin("viewer", "Viewer@123")}
                className="p-2.5 rounded-lg bg-slate-950 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 text-left transition-all group"
              >
                <span className="text-[11px] font-bold text-slate-300 block group-hover:text-white">Viewer</span>
                <span className="text-[9px] text-slate-400 block truncate">Read-only</span>
              </button>
            </div>
          </div>
        </div>

        <div className="text-center text-[11px] text-slate-400 flex items-center justify-center gap-4">
          <span>✓ HIPAA §164.312(b) Compliant</span>
          <span>✓ Safe Harbor 18 Redaction</span>
        </div>
      </div>
    </div>
  );
}
