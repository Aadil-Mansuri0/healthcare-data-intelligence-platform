"use client";

import { useState, useEffect } from "react";
import {
  getPlatformUsers,
  getSystemHealth,
  api,
} from "../../lib/api";
import {
  Users,
  ShieldCheck,
  UserPlus,
  Key,
  Server,
  Activity,
  CheckCircle2,
  AlertCircle,
  Loader2,
  RefreshCw,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function AdminPage() {
  return (
    <ProtectedRoute allowedRoles={["admin"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <AdminContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function AdminContent() {
  const [users, setUsers] = useState<any[]>([]);
  const [telemetry, setTelemetry] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  // New user form state
  const [showModal, setShowModal] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [newFullName, setNewFullName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("analyst");
  const [formMsg, setFormMsg] = useState("");
  const [creating, setCreating] = useState(false);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      getPlatformUsers().catch(() => ({ users: [] })),
      getSystemHealth().catch(() => null),
    ])
      .then(([usersRes, teleRes]) => {
        setUsers(usersRes.users || []);
        setTelemetry(teleRes);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setFormMsg("");
    try {
      await api.post("/api/auth/users", {
        username: newUsername,
        email: newEmail,
        full_name: newFullName,
        password: newPassword,
        role: newRole,
      });
      setFormMsg("User created successfully!");
      setNewUsername("");
      setNewEmail("");
      setNewFullName("");
      setNewPassword("");
      loadData();
      setTimeout(() => setShowModal(false), 1500);
    } catch (err: any) {
      setFormMsg(err?.response?.data?.detail || "Failed to create user.");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Users className="text-purple-400" size={22} />
            Enterprise Administration & RBAC Portal
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Role-Based Access Control, active credential audit, and platform infrastructure telemetry
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-lg shadow-purple-600/20"
        >
          <UserPlus size={14} /> Provision Platform User
        </button>
      </div>

      {/* System Telemetry Grid */}
      {telemetry && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="glass-panel rounded-2xl p-5 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Platform Gateway</span>
            <p className="text-sm font-bold text-white font-mono mt-1">
              {telemetry.platform_mode}
            </p>
            <span className="text-[10px] text-emerald-400 mt-2 block">
              ✓ {telemetry.services?.fastapi_gateway?.latency_ms}ms avg latency
            </span>
          </div>

          <div className="glass-panel rounded-2xl p-5 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Database Layer</span>
            <p className="text-sm font-bold text-white mt-1">
              {telemetry.services?.database_warehouse?.backend}
            </p>
            <span className="text-[10px] text-sky-400 mt-2 block">
              {telemetry.services?.database_warehouse?.active_connections} Pool Connections
            </span>
          </div>

          <div className="glass-panel rounded-2xl p-5 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Vector Store & Memory</span>
            <p className="text-sm font-bold text-white mt-1">ChromaDB / In-Memory</p>
            <span className="text-[10px] text-indigo-400 mt-2 block">
              {telemetry.services?.rag_knowledge_store?.documents_indexed} Documents Indexed
            </span>
          </div>

          <div className="glass-panel rounded-2xl p-5 border border-slate-800">
            <span className="text-xs text-slate-400 font-medium">Compute & Memory</span>
            <p className="text-sm font-bold text-white mt-1">
              {telemetry.system_load?.memory_usage}
            </p>
            <span className="text-[10px] text-purple-400 mt-2 block">
              CPU: {telemetry.system_load?.cpu_utilization}
            </span>
          </div>
        </div>
      )}

      {/* User Directory Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
            <Key size={16} className="text-purple-400" />
            Registered Platform Users & Role Assignment
          </h2>
          <span className="text-[11px] text-slate-400 font-mono">
            {users.length} authenticated principals
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-2.5 font-semibold">Username</th>
                <th className="pb-2.5 font-semibold">Full Name</th>
                <th className="pb-2.5 font-semibold">Email</th>
                <th className="pb-2.5 font-semibold">Assigned Role</th>
                <th className="pb-2.5 font-semibold">Status</th>
                <th className="pb-2.5 font-semibold">Last Active</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {users.map((u, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors font-mono text-[11px]">
                  <td className="py-3 font-bold text-white">{u.username}</td>
                  <td className="py-3 text-slate-200 font-sans">{u.full_name}</td>
                  <td className="py-3 text-slate-400">{u.email}</td>
                  <td className="py-3 font-sans">
                    <span
                      className={`inline-block text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                        u.role === "admin"
                          ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                          : u.role === "analyst"
                          ? "bg-sky-500/20 text-sky-300 border border-sky-500/30"
                          : "bg-slate-800 text-slate-400 border border-slate-700"
                      }`}
                    >
                      {u.role}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="text-emerald-400 font-sans font-semibold">✓ {u.status}</span>
                  </td>
                  <td className="py-3 text-slate-500">{u.last_login}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provision User Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <UserPlus size={18} className="text-purple-400" />
              Provision New Platform User
            </h3>

            {formMsg && (
              <div className="p-3 bg-purple-500/10 border border-purple-500/30 text-purple-300 text-xs rounded-lg">
                {formMsg}
              </div>
            )}

            <form onSubmit={handleCreateUser} className="space-y-3 text-xs">
              <div>
                <label className="text-slate-400 block mb-1">Username</label>
                <input
                  value={newUsername}
                  onChange={(e) => setNewUsername(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Full Name</label>
                <input
                  value={newFullName}
                  onChange={(e) => setNewFullName(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Email</label>
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-purple-500"
                />
              </div>

              <div>
                <label className="text-slate-400 block mb-1">Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white outline-none focus:border-purple-500"
                >
                  <option value="viewer">Viewer (Read-only Dashboards)</option>
                  <option value="analyst">Analyst (All Gold + AI Features)</option>
                  <option value="admin">Admin (Full Access & User Management)</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-bold rounded-lg transition-colors"
                >
                  {creating ? "Provisioning..." : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
