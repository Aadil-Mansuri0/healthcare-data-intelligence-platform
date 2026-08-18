"use client";

import { useState, useEffect } from "react";
import {
  getStreamingClaims,
  getOpioidAlerts,
  StreamingEvent,
  OpioidAlert,
} from "../../lib/api";
import {
  Radio,
  AlertTriangle,
  Activity,
  ShieldAlert,
  Clock,
  Pill,
  Users,
  CheckCircle2,
  RefreshCw,
  Sliders,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function StreamingPage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <StreamingContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function StreamingContent() {
  const [claims, setClaims] = useState<StreamingEvent[]>([]);
  const [alerts, setAlerts] = useState<OpioidAlert[]>([]);
  const [threshold, setThreshold] = useState(15);
  const [isLive, setIsLive] = useState(true);
  const [loading, setLoading] = useState(true);

  const fetchData = () => {
    Promise.all([getStreamingClaims(16), getOpioidAlerts()])
      .then(([claimRes, alertRes]) => {
        setClaims(claimRes.events || []);
        setAlerts(alertRes.alerts || []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => {
      if (isLive) {
        getStreamingClaims(16).then((res) => setClaims(res.events || [])).catch(() => {});
      }
    }, 4000);
    return () => clearInterval(interval);
  }, [isLive]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Radio className="text-rose-400 animate-pulse" size={22} />
            Real-Time Opioid Surveillance & Streaming Console
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Sub-minute Kafka claims processing with sliding-window overutilization anomaly detection
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLive(!isLive)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
              isLive
                ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            <span className={`w-2 h-2 rounded-full ${isLive ? "bg-emerald-400 animate-ping" : "bg-slate-500"}`} />
            {isLive ? "Stream: Live" : "Stream: Paused"}
          </button>
          <button
            onClick={fetchData}
            className="p-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
          >
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* KPI Stream Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Kafka Topic</span>
          <p className="text-sm font-bold text-white font-mono mt-1">healthcare.claims.raw</p>
          <span className="text-[10px] text-emerald-400 mt-2 block">✓ 6 Partitions · Active Ingestion</span>
        </div>
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Stream Throughput</span>
          <p className="text-2xl font-black text-white mt-1">1,450 msg/s</p>
          <span className="text-[10px] text-sky-400 mt-2 block">Micro-batch to S3 Bronze</span>
        </div>
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Sliding Window</span>
          <p className="text-2xl font-black text-white mt-1">60 Minutes</p>
          <span className="text-[10px] text-indigo-400 mt-2 block">Per-Prescriber NPI Tracking</span>
        </div>
        <div className="glass-panel rounded-2xl p-5 border border-slate-800">
          <span className="text-xs text-slate-400 font-medium">Surveillance Threshold</span>
          <p className="text-2xl font-black text-rose-400 mt-1">{threshold} Claims / Hr</p>
          <span className="text-[10px] text-rose-400/80 mt-2 block">CMS Overutilization Benchmark</span>
        </div>
      </div>

      {/* Main Grid: Live Claims Table & Alerts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Live Claims Feed */}
        <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <Activity size={16} className="text-sky-400" />
              Incoming Medicare Claims Event Ticker
            </h2>
            <span className="text-[11px] text-slate-400 font-mono">buffer: 16 events</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400">
                  <th className="pb-2.5 font-semibold">Time</th>
                  <th className="pb-2.5 font-semibold">Claim ID</th>
                  <th className="pb-2.5 font-semibold">Prescriber NPI</th>
                  <th className="pb-2.5 font-semibold">Drug / Category</th>
                  <th className="pb-2.5 font-semibold">State</th>
                  <th className="pb-2.5 font-semibold">Gross Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {claims.map((c, idx) => (
                  <tr key={idx} className={`hover:bg-slate-800/30 transition-colors ${c.is_opioid ? "bg-rose-950/20" : ""}`}>
                    <td className="py-2.5 font-mono text-[11px] text-slate-400">{c.timestamp}</td>
                    <td className="py-2.5 font-mono text-[11px] text-sky-400">{c.claim_id}</td>
                    <td className="py-2.5 font-mono text-[11px]">{c.prscrbr_npi}</td>
                    <td className="py-2.5 font-medium">
                      <span className="text-white">{c.drug_name}</span>
                      {c.is_opioid && (
                        <span className="ml-2 text-[9px] font-bold uppercase bg-rose-500/20 text-rose-400 border border-rose-500/30 px-1.5 py-0.5 rounded">
                          Opioid
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 font-bold text-sky-300">{c.prscrbr_state_abrvtn}</td>
                    <td className="py-2.5 font-semibold text-white">${c.cost_usd.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right 1 Col: Opioid Alerts Feed */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <ShieldAlert size={16} className="text-rose-400" />
              Active Overutilization Alerts
            </h2>
            <span className="text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-full">
              {alerts.length} Flagged
            </span>
          </div>

          <div className="space-y-3">
            {alerts.map((a, idx) => (
              <div key={idx} className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      a.severity === "HIGH"
                        ? "bg-rose-500/20 text-rose-400 border border-rose-500/30 animate-pulse"
                        : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                    }`}
                  >
                    {a.severity} Severity
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">{a.detected_at}</span>
                </div>

                <div>
                  <p className="text-xs font-bold text-white">{a.prscrbr_name}</p>
                  <p className="text-[11px] text-slate-400">
                    NPI: {a.prscrbr_npi} · {a.specialty} ({a.prscrbr_state_abrvtn})
                  </p>
                </div>

                <div className="p-2 bg-slate-900 rounded-lg text-[11px] flex items-center justify-between">
                  <span className="text-slate-400">Claims in 60m:</span>
                  <span className="font-bold text-rose-400">
                    {a.claim_count_in_window} / {a.threshold} threshold
                  </span>
                </div>

                <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px]">
                  <span className="text-slate-500">{a.status}</span>
                  <button className="text-sky-400 hover:text-sky-300 font-medium">Review NPI</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
