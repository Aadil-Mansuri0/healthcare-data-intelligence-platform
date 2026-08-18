"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "../context/AuthContext";
import {
  LayoutDashboard,
  Sparkles,
  Bot,
  Activity,
  CheckCircle2,
  GitFork,
  ShieldCheck,
  Users,
  LogOut,
  ChevronRight,
  Database,
  Layers,
  Menu,
  X,
  Radio,
  FileText,
  LucideIcon,
} from "lucide-react";

interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
  roles?: string[];
  badge?: string;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const NAVIGATION_SECTIONS: NavSection[] = [
  {
    title: "ANALYTICS & INTELLIGENCE",
    items: [
      { name: "Executive Overview", href: "/dashboard", icon: LayoutDashboard },
      { name: "AI Insights & Reports", href: "/insights", icon: Sparkles, roles: ["admin", "analyst"], badge: "AI" },
      { name: "Clinical AI Copilot", href: "/chat", icon: Bot, roles: ["admin", "analyst"], badge: "RAG" },
    ],
  },
  {
    title: "REAL-TIME SURVEILLANCE",
    items: [
      { name: "Opioid & Claims Stream", href: "/streaming", icon: Radio, roles: ["admin", "analyst"], badge: "LIVE" },
    ],
  },
  {
    title: "DATA GOVERNANCE & TRUST",
    items: [
      { name: "Data Quality (GE)", href: "/data-quality", icon: CheckCircle2, roles: ["admin", "analyst"] },
      { name: "Medallion Lineage", href: "/lineage", icon: GitFork, roles: ["admin", "analyst"] },
      { name: "HIPAA Compliance", href: "/compliance", icon: ShieldCheck, roles: ["admin", "analyst"] },
    ],
  },
  {
    title: "PLATFORM CONTROL",
    items: [
      { name: "Admin & RBAC Portal", href: "/admin", icon: Users, roles: ["admin"] },
    ],
  },
];

export function AppShell({
  children,
  selectedYear,
  onYearChange,
}: {
  children: React.ReactNode;
  selectedYear?: number | null;
  onYearChange?: (year: number | null) => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, hasRole } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col md:flex-row">
      {/* Mobile top bar */}
      <div className="md:hidden flex items-center justify-between p-4 bg-slate-900 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-cyan-400 flex items-center justify-center text-slate-950 font-black text-lg shadow-lg">
            H
          </div>
          <span className="font-bold text-sm tracking-wide">Healthcare Platform</span>
        </div>
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-2 text-slate-400 hover:text-white rounded-lg bg-slate-800"
        >
          {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>

      {/* Sidebar */}
      <aside
        className={`fixed md:sticky top-0 left-0 z-40 h-screen w-64 bg-slate-950/95 md:bg-slate-900/60 backdrop-blur-xl border-r border-slate-800/80 flex flex-col transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        }`}
      >
        {/* Brand Header */}
        <div className="p-5 border-b border-slate-800/70 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-sky-400 via-cyan-500 to-indigo-600 flex items-center justify-center text-slate-950 font-black text-xl shadow-lg shadow-sky-500/20">
            🏥
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight text-white tracking-wide">
              HealthData <span className="text-sky-400">IQ</span>
            </h1>
            <p className="text-[11px] text-slate-400 font-medium">Enterprise Intelligence</p>
          </div>
        </div>

        {/* Navigation Sections */}
        <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
          {NAVIGATION_SECTIONS.map((section, sIdx) => {
            const visibleItems = section.items.filter(
              (item) => !item.roles || hasRole(item.roles)
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={sIdx}>
                <h2 className="px-3 text-[10px] font-semibold text-slate-400 tracking-wider mb-2">
                  {section.title}
                </h2>
                <div className="space-y-1">
                  {visibleItems.map((item) => {
                    const isActive = pathname === item.href;
                    const Icon = item.icon;
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setSidebarOpen(false)}
                        className={`flex items-center justify-between px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                          isActive
                            ? "bg-sky-500/15 text-sky-400 border border-sky-500/30 shadow-sm"
                            : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
                        }`}
                      >
                        <div className="flex items-center gap-2.5">
                          <Icon size={16} className={isActive ? "text-sky-400" : "text-slate-400"} />
                          <span>{item.name}</span>
                        </div>
                        {item.badge && (
                          <span
                            className={`text-[9px] font-semibold px-1.5 py-0.5 rounded-full ${
                              item.badge === "LIVE"
                                ? "bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse"
                                : item.badge === "AI"
                                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                                : "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                            }`}
                          >
                            {item.badge}
                          </span>
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* User Footer Card */}
        <div className="p-3 border-t border-slate-800/70 bg-slate-900/40">
          <div className="flex items-center justify-between bg-slate-950/80 rounded-xl p-2.5 border border-slate-800/80">
            <div className="flex items-center gap-2.5 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-sky-600/20 border border-sky-500/30 text-sky-400 flex items-center justify-center font-bold text-xs">
                {user?.username?.slice(0, 2).toUpperCase() || "US"}
              </div>
              <div className="truncate">
                <p className="text-xs font-semibold text-white truncate">{user?.full_name || user?.username || "Healthcare User"}</p>
                <span
                  className={`inline-block text-[10px] font-semibold uppercase px-1.5 py-0.2 rounded ${
                    user?.role === "admin"
                      ? "bg-purple-500/20 text-purple-300"
                      : user?.role === "analyst"
                      ? "bg-sky-500/20 text-sky-300"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {user?.role || "viewer"}
                </span>
              </div>
            </div>
            <button
              onClick={handleLogout}
              title="Sign Out"
              className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-lg transition-colors"
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-30 bg-slate-950/85 backdrop-blur-md border-b border-slate-800/80 px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
          {/* Breadcrumb & Pipeline Status */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span>Platform</span>
              <ChevronRight size={12} className="text-slate-600" />
              <span className="text-white font-medium capitalize">
                {pathname.replace("/", "") || "Dashboard"}
              </span>
            </div>

            <div className="hidden sm:flex items-center gap-1.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[11px] font-medium px-2.5 py-1 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>Gold DW Sync: Active</span>
            </div>
          </div>

          {/* Controls: Year Selector & Quick Badges */}
          <div className="flex items-center gap-3">
            {onYearChange && (
              <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-lg p-0.5 text-xs">
                {[
                  { label: "All Years", val: null },
                  { label: "2024", val: 2024 },
                  { label: "2023", val: 2023 },
                  { label: "2022", val: 2022 },
                ].map((item) => {
                  const isSelected = selectedYear === item.val;
                  return (
                    <button
                      key={item.label}
                      onClick={() => onYearChange(item.val)}
                      className={`px-2.5 py-1 rounded-md transition-all font-medium ${
                        isSelected
                          ? "bg-sky-600 text-white shadow-sm"
                          : "text-slate-400 hover:text-white"
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            )}

            <div className="hidden lg:flex items-center gap-2 text-xs text-slate-400 bg-slate-900/60 border border-slate-800/80 rounded-lg px-3 py-1.5">
              <Database size={13} className="text-sky-400" />
              <span>Medicare Part D (CMS PUF)</span>
            </div>
          </div>
        </header>

        {/* Page Body */}
        <div className="flex-1 p-6 md:p-8 max-w-7xl w-full mx-auto">{children}</div>
      </main>
    </div>
  );
}
