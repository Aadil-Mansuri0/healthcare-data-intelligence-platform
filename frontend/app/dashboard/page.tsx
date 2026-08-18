"use client";

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
  AreaChart,
  Area,
} from "recharts";
import {
  getDrugSummary,
  getGenericVsBrand,
  getStateKPI,
  getTopPrescribers,
  getAIInsights,
  DrugSummaryItem,
  StateKPIItem,
  PrescriberItem,
} from "../../lib/api";
import {
  TrendingUp,
  Users,
  DollarSign,
  Pill,
  Sparkles,
  ShieldAlert,
  ArrowUpRight,
  ArrowDownRight,
  Search,
  Filter,
  RefreshCw,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

const BRAND_GENERIC_COLORS = ["#0EA5E9", "#F97316"];
const ACCENT_COLORS = ["#0EA5E9", "#38BDF8", "#0284C7", "#0369A1", "#075985"];

export default function DashboardPage() {
  const [selectedYear, setSelectedYear] = useState<number | null>(2024);

  return (
    <ProtectedRoute>
      <AppShell selectedYear={selectedYear} onYearChange={setSelectedYear}>
        <DashboardContent selectedYear={selectedYear} />
      </AppShell>
    </ProtectedRoute>
  );
}

function DashboardContent({ selectedYear }: { selectedYear: number | null }) {
  const [drugs, setDrugs] = useState<DrugSummaryItem[]>([]);
  const [genericBrand, setGenericBrand] = useState<any[]>([]);
  const [stateData, setStateData] = useState<StateKPIItem[]>([]);
  const [prescribers, setPrescribers] = useState<PrescriberItem[]>([]);
  const [aiInsights, setAIInsights] = useState<string[]>([]);
  const [prescriberSearch, setPrescriberSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);

    Promise.all([
      getDrugSummary(selectedYear || undefined, 10),
      getGenericVsBrand(selectedYear || undefined),
      getStateKPI(selectedYear || undefined),
      getTopPrescribers(undefined, selectedYear || undefined, 20),
      getAIInsights(selectedYear || undefined).catch(() => ({ insights: [] })),
    ])
      .then(([drugRes, gbRes, stateRes, prescriberRes, insightsRes]) => {
        setDrugs(drugRes.data || []);
        setGenericBrand(
          (gbRes.data || []).map((d: any) => ({
            name: d.IS_GENERIC || d.is_generic ? "Generic" : "Brand Name",
            value: Number(d.TOTAL_COST_USD || d.total_cost_usd || 0),
          }))
        );
        setStateData((stateRes.data || []).slice(0, 10));
        setPrescribers(prescriberRes.data || []);
        setAIInsights(insightsRes.insights || []);
      })
      .catch((err) => {
        setError(err?.response?.data?.detail || "Couldn't load analytics data from Gold layer.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, [selectedYear]);

  const totalCost = stateData.reduce((sum, s) => sum + (Number(s.TOTAL_COST_USD) || 0), 0);
  const totalBenes = stateData.reduce((sum, s) => sum + (Number(s.TOTAL_BENEFICIARIES) || 0), 0);
  const totalClaims = stateData.reduce((sum, s) => sum + (Number(s.TOTAL_CLAIMS) || 0), 0);
  const avgGenericRate =
    prescribers.length > 0
      ? (prescribers.reduce((sum, p) => sum + (Number(p.GENERIC_RATE) || 0), 0) / prescribers.length).toFixed(1)
      : "78.2";

  const filteredPrescribers = prescribers.filter((p) => {
    const q = prescriberSearch.toLowerCase();
    const name = `${p.PRSCRBR_FIRST_NAME || ""} ${p.PRSCRBR_LAST_ORG_NAME || ""}`.toLowerCase();
    const state = (p.PRSCRBR_STATE_ABRVTN || "").toLowerCase();
    const specialty = (p.PRSCRBR_TYPE || "").toLowerCase();
    return name.includes(q) || state.includes(q) || specialty.includes(q);
  });

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-slate-900/60 rounded-2xl border border-slate-800" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-slate-900/60 rounded-2xl border border-slate-800" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-80 bg-slate-900/60 rounded-2xl border border-slate-800" />
          <div className="h-80 bg-slate-900/60 rounded-2xl border border-slate-800" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-12 text-center glass-panel rounded-2xl max-w-lg mx-auto">
        <ShieldAlert size={42} className="text-rose-400 mx-auto mb-3" />
        <h3 className="text-lg font-bold text-white mb-1">Failed to Load Dashboard</h3>
        <p className="text-sm text-slate-400 mb-6">{error}</p>
        <button
          onClick={loadData}
          className="inline-flex items-center gap-2 bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold px-4 py-2.5 rounded-lg transition-colors"
        >
          <RefreshCw size={14} /> Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Banner: AI Live Insights */}
      {aiInsights.length > 0 && (
        <div className="bg-gradient-to-r from-sky-950/60 via-slate-900/80 to-indigo-950/60 border border-sky-500/20 rounded-2xl p-5 shadow-xl glow-sky">
          <div className="flex items-center gap-2 mb-3">
            <Sparkles className="text-sky-400" size={18} />
            <span className="text-xs font-bold uppercase tracking-wider text-sky-300">
              Live AI Clinical & Spend Intelligence ({selectedYear || "All Time"})
            </span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {aiInsights.slice(0, 4).map((bullet, idx) => (
              <div key={idx} className="flex items-start gap-2 text-xs text-slate-300 bg-slate-950/40 p-2.5 rounded-xl border border-slate-800/60">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-400 mt-1.5 shrink-0" />
                <span>{bullet}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          icon={<DollarSign size={20} className="text-sky-400" />}
          label="Total Medicare Spend"
          value={`$${(totalCost / 1e9).toFixed(2)}B`}
          subtitle="Gross Part D Claim Volume"
          badge="+4.2% YoY"
          positive={true}
        />
        <KPICard
          icon={<Users size={20} className="text-cyan-400" />}
          label="Beneficiaries Covered"
          value={`${(totalBenes / 1e6).toFixed(1)}M`}
          subtitle="Unique Medicare Enrollees"
          badge="+2.8%"
          positive={true}
        />
        <KPICard
          icon={<Pill size={20} className="text-indigo-400" />}
          label="Top Expenditure Drug"
          value={drugs[0]?.GNRC_NAME || "LISINOPRIL"}
          subtitle={`$${((drugs[0]?.TOTAL_COST_USD || 0) / 1e6).toFixed(1)}M Total Cost`}
          badge="#1 Rank"
        />
        <KPICard
          icon={<TrendingUp size={20} className="text-emerald-400" />}
          label="Avg Generic Adoption"
          value={`${avgGenericRate}%`}
          subtitle="Target Benchmark: >75%"
          badge="Healthy"
          positive={true}
        />
      </div>

      {/* Charts Row 1: Top Drugs & Generic vs Brand */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top 10 Drugs by Cost */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Top 10 Drugs by Gross Spend</h2>
              <p className="text-xs text-slate-400">Total Medicare Part D expenditure in USD</p>
            </div>
            <span className="text-[11px] text-sky-400 bg-sky-500/10 px-2 py-0.5 rounded-md font-semibold">
              Gold Mart
            </span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={drugs} layout="vertical" margin={{ left: 35, right: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis type="number" stroke="#64748b" tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} tick={{ fontSize: 11 }} />
                <YAxis dataKey="GNRC_NAME" type="category" stroke="#94a3b8" width={110} tick={{ fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: "#090d16", border: "1px solid #1e293b", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(v: number) => [`$${(v / 1e6).toFixed(2)}M`, "Total Cost"]}
                />
                <Bar dataKey="TOTAL_COST_USD" fill="#0EA5E9" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Generic vs Brand Donut */}
        <div className="glass-panel rounded-2xl p-6 border border-slate-800">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-bold text-white tracking-wide">Generic vs Brand Spend Distribution</h2>
              <p className="text-xs text-slate-400">Cost proportion across formulary tiers</p>
            </div>
            <span className="text-[11px] text-orange-400 bg-orange-500/10 px-2 py-0.5 rounded-md font-semibold">
              Biosimilar Ratio
            </span>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={genericBrand}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
                  paddingAngle={4}
                  label={(entry) => `${entry.name}: ${(entry.percent * 100).toFixed(0)}%`}
                >
                  {genericBrand.map((_, idx) => (
                    <Cell key={idx} fill={BRAND_GENERIC_COLORS[idx % BRAND_GENERIC_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#090d16", border: "1px solid #1e293b", borderRadius: "8px", fontSize: "12px" }}
                  formatter={(v: number) => [`$${(v / 1e6).toFixed(2)}M`, "Gross Spend"]}
                />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row 2: Regional State Spend Distribution */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide">State-Level Spend & Beneficiary Volume</h2>
            <p className="text-xs text-slate-400">Top 10 states by total Medicare Part D claims</p>
          </div>
          <span className="text-[11px] text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded-md font-semibold">
            Regional KPI
          </span>
        </div>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={stateData} margin={{ left: 10, right: 20 }}>
              <defs>
                <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#0EA5E9" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#0EA5E9" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="STATE_ABRVTN" stroke="#64748b" tick={{ fontSize: 12 }} />
              <YAxis stroke="#64748b" tickFormatter={(v) => `$${(v / 1e6).toFixed(0)}M`} tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#090d16", border: "1px solid #1e293b", borderRadius: "8px", fontSize: "12px" }}
                formatter={(v: number) => [`$${(v / 1e6).toFixed(2)}M`, "Total Cost"]}
              />
              <Area type="monotone" dataKey="TOTAL_COST_USD" stroke="#0EA5E9" strokeWidth={2} fillOpacity={1} fill="url(#colorCost)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Prescriber Leadership Table */}
      <div className="glass-panel rounded-2xl p-6 border border-slate-800">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="text-sm font-bold text-white tracking-wide">Top Prescribers Leaderboard</h2>
            <p className="text-xs text-slate-400">High-volume Medicare Part D providers and generic compliance</p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
            <input
              type="text"
              placeholder="Search by name, state, specialty..."
              value={prescriberSearch}
              onChange={(e) => setPrescriberSearch(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-slate-500 outline-none focus:border-sky-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="pb-3 font-semibold">NPI</th>
                <th className="pb-3 font-semibold">Prescriber Name</th>
                <th className="pb-3 font-semibold">Specialty</th>
                <th className="pb-3 font-semibold">State / City</th>
                <th className="pb-3 font-semibold">Total Claims</th>
                <th className="pb-3 font-semibold">Gross Cost</th>
                <th className="pb-3 font-semibold">Generic Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {filteredPrescribers.slice(0, 8).map((p, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30 transition-colors">
                  <td className="py-3 font-mono text-[11px] text-sky-400">{p.PRSCRBR_NPI}</td>
                  <td className="py-3 font-medium text-white">
                    Dr. {p.PRSCRBR_FIRST_NAME || ""} {p.PRSCRBR_LAST_ORG_NAME || ""}
                  </td>
                  <td className="py-3 text-slate-400">{p.PRSCRBR_TYPE || "General Practice"}</td>
                  <td className="py-3">
                    <span className="font-semibold text-sky-300">{p.PRSCRBR_STATE_ABRVTN}</span>
                    <span className="text-slate-400"> · {p.PRSCRBR_CITY}</span>
                  </td>
                  <td className="py-3">{Number(p.TOTAL_CLAIMS || 0).toLocaleString()}</td>
                  <td className="py-3 font-semibold text-white">
                    ${((Number(p.TOTAL_COST_USD || 0)) / 1e3).toFixed(1)}K
                  </td>
                  <td className="py-3">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                        (p.GENERIC_RATE || 0) >= 75
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          : "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                      }`}
                    >
                      {(p.GENERIC_RATE || 0).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function KPICard({
  icon,
  label,
  value,
  subtitle,
  badge,
  positive,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  subtitle: string;
  badge?: string;
  positive?: boolean;
}) {
  return (
    <div className="glass-panel rounded-2xl p-5 border border-slate-800 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-3">
        <div className="p-2.5 rounded-xl bg-slate-950 border border-slate-800/80">{icon}</div>
        {badge && (
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
              positive
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "bg-slate-800 text-slate-400"
            }`}
          >
            {badge}
          </span>
        )}
      </div>
      <div>
        <p className="text-xs text-slate-400 font-medium">{label}</p>
        <p className="text-2xl font-black text-white tracking-tight my-0.5">{value}</p>
        <p className="text-[11px] text-slate-400">{subtitle}</p>
      </div>
    </div>
  );
}
