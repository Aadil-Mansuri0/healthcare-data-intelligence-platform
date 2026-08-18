"use client";

import { useState, useEffect } from "react";
import {
  testPHIRedaction,
  getComplianceAuditLogs,
} from "../../lib/api";
import {
  ShieldCheck,
  Lock,
  FileCheck,
  Eye,
  AlertOctagon,
  RefreshCw,
  Loader2,
  Check,
  Shield,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function CompliancePage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <ComplianceContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function ComplianceContent() {
  const [testInput, setTestInput] = useState(
    "Patient Jane Doe (SSN: 123-45-6789, Phone: 555-839-2041, Email: jane.doe@hospital.org) was prescribed Oxycodone on 04/12/2024 by Dr. Smith (NPI: 1000000412, MRN: 48291) at client IP 192.168.1.45."
  );
  const [redactionResult, setRedactionResult] = useState<any>(null);
  const [redactionLoading, setRedactionLoading] = useState(false);

  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const runRedactionTest = () => {
    if (!testInput.trim()) return;
    setRedactionLoading(true);
    testPHIRedaction(testInput)
      .then((res) => setRedactionResult(res))
      .catch(() => {})
      .finally(() => setRedactionLoading(false));
  };

  const loadAuditLogs = () => {
    setAuditLoading(true);
    getComplianceAuditLogs(50)
      .then((res) => setAuditLogs(res.records || []))
      .catch(() => {})
      .finally(() => setAuditLoading(false));
  };

  useEffect(() => {
    runRedactionTest();
    loadAuditLogs();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldCheck className="text-cyan-400" size={22} />
            HIPAA Security & Safe Harbor 18 PHI Compliance Center
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            45 CFR §164.514(b)(2) automated de-identification sandbox & §164.312(b) audit trail control tower
          </p>
        </div>

        <div className="flex items-center gap-2 bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 text-xs px-3 py-1.5 rounded-lg">
          <Shield size={14} />
          <span>Safe Harbor 18 Guard: Active</span>
        </div>
      </div>

      {/* KPI Policy Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">De-Identification Standard</span>
          <p className="text-sm font-bold text-white mt-1">HIPAA Safe Harbor</p>
          <span className="text-[10px] text-cyan-400 mt-2 block">18 Direct Identifiers Auto-Redacted</span>
        </div>
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Audit Control Mandate</span>
          <p className="text-sm font-bold text-white mt-1">45 CFR §164.312(b)</p>
          <span className="text-[10px] text-emerald-400 mt-2 block">All PHI-adjacent Routes Logged</span>
        </div>
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Retention Policy</span>
          <p className="text-sm font-bold text-white mt-1">7 Years Immutable</p>
          <span className="text-[10px] text-indigo-400 mt-2 block">AUDIT.PHI_ACCESS_LOG Partitioning</span>
        </div>
      </div>

      {/* PHI Redaction Sandbox */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
            <Lock size={16} className="text-cyan-400" />
            Interactive PHI Redaction Sandbox
          </h2>
          <span className="text-[11px] text-slate-400 font-mono">Simulates pre-LLM redaction pipeline</span>
        </div>

        <div className="space-y-3">
          <label className="text-xs text-slate-400 font-medium block">
            Clinical Input Text (Type or edit identifiers below):
          </label>
          <textarea
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            rows={3}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs text-slate-200 outline-none focus:border-cyan-500 font-mono leading-relaxed"
          />

          <button
            onClick={runRedactionTest}
            disabled={redactionLoading}
            className="inline-flex items-center gap-1.5 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-slate-950 font-bold text-xs px-4 py-2 rounded-lg transition-colors shadow-lg shadow-cyan-500/20"
          >
            {redactionLoading ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={14} />}
            Execute Safe Harbor Redactor
          </button>
        </div>

        {redactionResult && (
          <div className="space-y-3 pt-2">
            <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold text-cyan-400 uppercase font-mono">
                  Safe-To-Send Redacted Output (Sent to OpenAI/RAG):
                </span>
                <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">
                  {redactionResult.total_phi_patterns_detected} Pattern(s) Stripped
                </span>
              </div>
              <p className="text-xs font-mono text-emerald-300 leading-relaxed bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                {redactionResult.redacted_text}
              </p>
            </div>

            {Object.keys(redactionResult.findings_by_category || {}).length > 0 && (
              <div className="flex flex-wrap gap-2 text-[10px]">
                {Object.entries(redactionResult.findings_by_category).map(([cat, count]) => (
                  <span key={cat} className="bg-slate-950 border border-slate-800 px-2.5 py-1 rounded-lg text-slate-300 font-mono">
                    <strong className="text-cyan-400 uppercase">{cat}:</strong> {String(count)} stripped
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* HIPAA Audit Log Viewer */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
            <FileCheck size={16} className="text-emerald-400" />
            HIPAA §164.312(b) Access Audit Control Trail
          </h2>
          <button
            onClick={loadAuditLogs}
            className="text-xs text-slate-400 hover:text-white flex items-center gap-1"
          >
            <RefreshCw size={12} /> Refresh Logs
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-2.5 font-semibold">Time (UTC)</th>
                <th className="pb-2.5 font-semibold">User</th>
                <th className="pb-2.5 font-semibold">Method</th>
                <th className="pb-2.5 font-semibold">Path</th>
                <th className="pb-2.5 font-semibold">Status</th>
                <th className="pb-2.5 font-semibold">Latency</th>
                <th className="pb-2.5 font-semibold">Client IP</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {auditLogs.map((log, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors font-mono text-[11px]">
                  <td className="py-2.5 text-slate-400">{log.accessed_at?.slice(11, 19) || "12:00:00"}</td>
                  <td className="py-2.5 font-bold text-sky-300">{log.username || "anonymous"}</td>
                  <td className="py-2.5 text-slate-400">{log.method}</td>
                  <td className="py-2.5 text-cyan-300 truncate max-w-[200px]">{log.path}</td>
                  <td className="py-2.5">
                    <span className="text-emerald-400 font-semibold">{log.status_code}</span>
                  </td>
                  <td className="py-2.5 text-slate-400">{log.duration_ms}ms</td>
                  <td className="py-2.5 text-slate-500">{log.client_ip}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
