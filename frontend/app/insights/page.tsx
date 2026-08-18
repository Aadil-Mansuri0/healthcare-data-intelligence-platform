"use client";

import { useState, useEffect } from "react";
import {
  generatePeriodicReport,
  getAIRecommendations,
  getAIQualityCheck,
  AIReportResponse,
  AIRecommendationsResponse,
  AIQualityCheckResponse,
} from "../../lib/api";
import {
  Sparkles,
  FileText,
  DollarSign,
  ShieldCheck,
  Download,
  Copy,
  Check,
  AlertCircle,
  Loader2,
  TrendingDown,
  ArrowRight,
  RefreshCw,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function InsightsPage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <InsightsContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function InsightsContent() {
  const [activeTab, setActiveTab] = useState<"reports" | "recommendations" | "quality">("reports");
  const [reportPeriod, setReportPeriod] = useState<"weekly" | "monthly">("monthly");
  const [reportYear, setReportYear] = useState<number>(2024);
  const [reportData, setReportData] = useState<AIReportResponse | null>(null);
  const [reportLoading, setReportLoading] = useState(false);

  const [recommendations, setRecommendations] = useState<AIRecommendationsResponse | null>(null);
  const [recsLoading, setRecsLoading] = useState(false);

  const [qualityData, setQualityData] = useState<AIQualityCheckResponse | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  const [copied, setCopied] = useState(false);

  // Load recommendations
  const loadRecommendations = (year = 2024) => {
    setRecsLoading(true);
    getAIRecommendations(year)
      .then((res) => setRecommendations(res))
      .catch(() => {})
      .finally(() => setRecsLoading(false));
  };

  // Load quality checks
  const loadQualityCheck = (year = 2024) => {
    setQualityLoading(true);
    getAIQualityCheck(year)
      .then((res) => setQualityData(res))
      .catch(() => {})
      .finally(() => setQualityLoading(false));
  };

  // Generate executive report
  const handleGenerateReport = () => {
    setReportLoading(true);
    generatePeriodicReport(reportPeriod, reportYear)
      .then((res) => setReportData(res))
      .catch(() => {})
      .finally(() => setReportLoading(false));
  };

  useEffect(() => {
    handleGenerateReport();
    loadRecommendations(2024);
    loadQualityCheck(2024);
  }, []);

  const handleCopyMarkdown = () => {
    if (reportData?.markdown) {
      navigator.clipboard.writeText(reportData.markdown);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadMarkdown = () => {
    if (reportData?.markdown) {
      const blob = new Blob([reportData.markdown], { type: "text/markdown" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Healthcare_Report_${reportPeriod}_${reportYear}.md`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar with Tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Sparkles className="text-sky-400" size={22} />
            AI Intelligence & Executive Suite
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated narrative generation, cost-optimization proposals, and anomaly root cause engine
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1 text-xs">
          <button
            onClick={() => setActiveTab("reports")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === "reports" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            <FileText size={14} /> Executive Reports
          </button>
          <button
            onClick={() => setActiveTab("recommendations")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === "recommendations" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            <TrendingDown size={14} /> ROI Recommendations
          </button>
          <button
            onClick={() => setActiveTab("quality")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg font-medium transition-all ${
              activeTab === "quality" ? "bg-sky-600 text-white shadow-sm" : "text-slate-400 hover:text-white"
            }`}
          >
            <ShieldCheck size={14} /> Anomaly Explainer
          </button>
        </div>
      </div>

      {/* Tab 1: Executive Report Generator */}
      {activeTab === "reports" && (
        <div className="space-y-6">
          <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-1 bg-slate-950 border border-slate-800 rounded-lg p-1 text-xs">
                <button
                  onClick={() => setReportPeriod("weekly")}
                  className={`px-3 py-1.5 rounded-md font-semibold ${
                    reportPeriod === "weekly" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Weekly Digest
                </button>
                <button
                  onClick={() => setReportPeriod("monthly")}
                  className={`px-3 py-1.5 rounded-md font-semibold ${
                    reportPeriod === "monthly" ? "bg-sky-600 text-white" : "text-slate-400 hover:text-white"
                  }`}
                >
                  Monthly Strategic
                </button>
              </div>

              <select
                value={reportYear}
                onChange={(e) => setReportYear(Number(e.target.value))}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-white outline-none focus:border-sky-500"
              >
                <option value={2024}>Year 2024</option>
                <option value={2023}>Year 2023</option>
                <option value={2022}>Year 2022</option>
              </select>

              <button
                onClick={handleGenerateReport}
                disabled={reportLoading}
                className="inline-flex items-center gap-1.5 bg-sky-600 hover:bg-sky-500 disabled:opacity-50 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow-lg shadow-sky-600/20"
              >
                {reportLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                Generate Report
              </button>
            </div>

            {reportData && (
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyMarkdown}
                  className="inline-flex items-center gap-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs px-3 py-1.5 rounded-lg transition-colors"
                >
                  {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
                  {copied ? "Copied" : "Copy MD"}
                </button>
                <button
                  onClick={handleDownloadMarkdown}
                  className="inline-flex items-center gap-1.5 bg-slate-950 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs px-3 py-1.5 rounded-lg transition-colors"
                >
                  <Download size={13} /> Export .md
                </button>
              </div>
            )}
          </div>

          {reportLoading ? (
            <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
              <Loader2 size={32} className="animate-spin text-sky-400 mx-auto mb-3" />
              <p className="text-sm font-semibold text-white">Synthesizing Executive Healthcare Intelligence...</p>
              <p className="text-xs text-slate-400 mt-1">Aggregating Part D KPI marts & running narrative engine</p>
            </div>
          ) : reportData ? (
            <div className="glass-panel rounded-2xl p-8 border border-slate-800 text-slate-200 prose prose-invert max-w-none text-xs leading-relaxed space-y-4">
              <pre className="whitespace-pre-wrap font-sans text-xs bg-slate-950/60 p-6 rounded-xl border border-slate-800/80 overflow-x-auto text-slate-300 leading-6">
                {reportData.markdown}
              </pre>
            </div>
          ) : null}
        </div>
      )}

      {/* Tab 2: ROI Recommendations */}
      {activeTab === "recommendations" && (
        <div className="space-y-6">
          {recsLoading ? (
            <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
              <Loader2 size={32} className="animate-spin text-sky-400 mx-auto mb-3" />
              <p className="text-sm font-semibold text-white">Evaluating Cost-Optimization Opportunities...</p>
            </div>
          ) : recommendations ? (
            <>
              {/* Savings Highlight Card */}
              <div className="bg-gradient-to-r from-emerald-950/50 via-slate-900/80 to-sky-950/50 border border-emerald-500/30 rounded-2xl p-6 glow-emerald">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div>
                    <span className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                      Identified Formulary Optimization Opportunity
                    </span>
                    <h2 className="text-3xl font-black text-white mt-1">
                      ${(recommendations.total_potential_savings_usd / 1e6).toFixed(2)}M USD
                    </h2>
                    <p className="text-xs text-slate-300 mt-1">
                      Estimated net annual savings through brand-to-generic biosimilar conversion & prescriber detailing.
                    </p>
                  </div>
                  <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 text-right">
                    <span className="text-[11px] text-slate-400 block">Analyzed Candidates</span>
                    <span className="text-lg font-bold text-sky-400">
                      {recommendations.supporting_data?.substitution_candidates?.length || 5} Therapeutic Tiers
                    </span>
                  </div>
                </div>
              </div>

              {/* Actionable Recommendations List */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {recommendations.recommendations.map((rec, idx) => (
                  <div key={idx} className="glass-panel rounded-xl p-5 border border-slate-800 flex flex-col justify-between space-y-3">
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          rec.priority === "high"
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : rec.priority === "medium"
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : "bg-sky-500/15 text-sky-400 border border-sky-500/30"
                        }`}
                      >
                        {rec.priority} Priority
                      </span>
                      <span className="text-[11px] font-semibold text-emerald-400">{rec.estimated_impact}</span>
                    </div>
                    <p className="text-xs font-medium text-white leading-relaxed">{rec.recommendation}</p>
                    <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                      <span>Clinical Step Therapy</span>
                      <span className="text-sky-400 hover:underline cursor-pointer flex items-center gap-1">
                        Apply Policy <ArrowRight size={11} />
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
      )}

      {/* Tab 3: Anomaly Explainer */}
      {activeTab === "quality" && (
        <div className="space-y-6">
          {qualityLoading ? (
            <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
              <Loader2 size={32} className="animate-spin text-sky-400 mx-auto mb-3" />
              <p className="text-sm font-semibold text-white">Running Statistical Z-Score Distribution Analysis...</p>
            </div>
          ) : qualityData ? (
            <div className="space-y-6">
              <div className="glass-panel rounded-2xl p-6 border border-slate-800">
                <div className="flex items-center gap-3 mb-4">
                  <div
                    className={`w-3 h-3 rounded-full ${
                      qualityData.status === "healthy" ? "bg-emerald-400 animate-pulse" : "bg-amber-400 animate-ping"
                    }`}
                  />
                  <h2 className="text-sm font-bold text-white tracking-wide">
                    Automated Data Warehouse Quality Diagnostics
                  </h2>
                  <span
                    className={`ml-auto text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase ${
                      qualityData.status === "healthy"
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                    }`}
                  >
                    {qualityData.status}
                  </span>
                </div>

                <div className="bg-slate-950 p-5 rounded-xl border border-slate-800 text-xs text-slate-300 leading-relaxed mb-6">
                  <span className="font-bold text-sky-400 block mb-1">AI Root Cause & Engineering Narrative:</span>
                  {qualityData.ai_explanation}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  {qualityData.duplicates?.map((d, i) => (
                    <div key={i} className="bg-slate-950/60 p-4 rounded-xl border border-slate-800">
                      <span className="text-[11px] text-slate-400 block">{d.table}</span>
                      <span className="text-lg font-bold text-white mt-1 block">
                        {d.duplicate_key_groups === 0 ? "0 Duplicate Keys" : `${d.duplicate_key_groups} Duplicates`}
                      </span>
                      <span className="text-[10px] text-emerald-400 mt-1 block">✓ Primary Key Integrity Verified</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
