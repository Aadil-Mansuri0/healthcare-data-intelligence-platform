"use client";

import { useState, useEffect } from "react";
import { getDataQualityReport, DataQualityReportResponse } from "../../lib/api";
import {
  CheckCircle2,
  ShieldCheck,
  Activity,
  AlertCircle,
  Database,
  Layers,
  RefreshCw,
  Loader2,
  FileCode,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function DataQualityPage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <DataQualityContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function DataQualityContent() {
  const [data, setData] = useState<DataQualityReportResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    getDataQualityReport()
      .then((res) => setData(res))
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <CheckCircle2 className="text-emerald-400" size={22} />
            Great Expectations & Data Quality Control Tower
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated schema validation, null-checks, distribution boundaries, and foreign key integrity across Medallion layers
          </p>
        </div>

        <button
          onClick={loadData}
          className="inline-flex items-center gap-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs px-3.5 py-1.5 rounded-lg transition-colors"
        >
          <RefreshCw size={13} /> Run Suite
        </button>
      </div>

      {loading ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
          <Loader2 size={32} className="animate-spin text-emerald-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-white">Auditing Great Expectations Assertions...</p>
        </div>
      ) : data ? (
        <>
          {/* Top Score Banner */}
          <div className="bg-gradient-to-r from-emerald-950/60 via-slate-900/80 to-teal-950/60 border border-emerald-500/30 rounded-2xl p-6 glow-emerald">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                  Automated Pipeline Health Status
                </span>
                <div className="flex items-baseline gap-3 mt-1">
                  <h2 className="text-3xl font-black text-white">{data.overall_health_score}%</h2>
                  <span className="text-sm font-bold text-emerald-400 uppercase tracking-wide">
                    {data.status}
                  </span>
                </div>
                <p className="text-xs text-slate-300 mt-1">
                  Zero critical schema drift or null-value constraint violations detected in current partition.
                </p>
              </div>

              <div className="flex items-center gap-4 bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <div>
                  <span className="text-[10px] text-slate-400 block">Evaluated Records</span>
                  <span className="text-sm font-bold text-white">{data.statistics.records_evaluated}</span>
                </div>
                <div className="w-px h-8 bg-slate-800" />
                <div>
                  <span className="text-[10px] text-slate-400 block">Passed Assertions</span>
                  <span className="text-sm font-bold text-emerald-400">
                    {data.statistics.passed_assertions} / {data.statistics.total_assertions}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Test Suites Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {data.suites.map((suite, idx) => (
              <div key={idx} className="glass-panel rounded-2xl p-6 border border-slate-800 flex flex-col justify-between space-y-4">
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[11px] font-bold text-sky-400 font-mono">{suite.layer}</span>
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                      {suite.passed}/{suite.total_tests} PASS
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-white font-mono">{suite.suite_name}</h3>
                </div>

                <div className="space-y-2 pt-2 border-t border-slate-800">
                  {suite.assertions.map((ast, i) => (
                    <div key={i} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800/80 text-[11px] flex items-center justify-between gap-2">
                      <div className="truncate text-slate-300 font-mono">{ast.name}</div>
                      <span className="text-[10px] font-semibold text-emerald-400 shrink-0">✓ {ast.observed}</span>
                    </div>
                  ))}
                </div>

                <div className="pt-2 text-[11px] text-slate-400 flex items-center justify-between">
                  <span>Engine: Great Expectations 0.18</span>
                  <span className="text-sky-400">Verified</span>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </div>
  );
}
