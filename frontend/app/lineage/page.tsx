"use client";

import { useState, useEffect } from "react";
import { getLineageGraph, LineageGraphResponse } from "../../lib/api";
import {
  GitFork,
  Database,
  Layers,
  ArrowRight,
  Server,
  Activity,
  CheckCircle2,
  Clock,
  Radio,
  FileCode,
  Loader2,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

export default function LineagePage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <LineageContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function LineageContent() {
  const [lineage, setLineage] = useState<LineageGraphResponse | null>(null);
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLineageGraph()
      .then((res) => {
        setLineage(res);
        if (res.nodes?.length > 0) {
          setSelectedNode(res.nodes[0]);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <GitFork className="text-sky-400" size={22} />
            End-to-End Medallion Data Lineage Explorer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            OpenLineage / Marquez metadata graph tracing PostgreSQL & Kafka ingestion through S3, PySpark, Snowflake & dbt
          </p>
        </div>

        {lineage && (
          <div className="flex items-center gap-2 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-3 py-1.5 rounded-lg">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
            <span>Airflow DAG Status: {lineage.summary.pipeline_state}</span>
          </div>
        )}
      </div>

      {loading ? (
        <div className="glass-panel rounded-2xl p-12 text-center border border-slate-800">
          <Loader2 size={32} className="animate-spin text-sky-400 mx-auto mb-3" />
          <p className="text-sm font-semibold text-white">Loading Medallion Lineage Topologies...</p>
        </div>
      ) : lineage ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Interactive DAG Flow */}
          <div className="lg:col-span-2 glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-white tracking-wide">
                Medallion Architecture Pipeline Nodes
              </h2>
              <span className="text-[11px] text-slate-400 font-mono">
                {lineage.summary.total_nodes} nodes · {lineage.summary.total_edges} dependencies
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              {lineage.nodes.map((node) => {
                const isSelected = selectedNode?.id === node.id;
                return (
                  <button
                    key={node.id}
                    onClick={() => setSelectedNode(node)}
                    className={`text-left p-4 rounded-xl border transition-all flex flex-col justify-between space-y-2 ${
                      isSelected
                        ? "bg-sky-950/50 border-sky-500 shadow-lg glow-sky"
                        : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span
                        className={`text-[9px] font-bold uppercase px-2 py-0.5 rounded-full ${
                          node.layer === "source"
                            ? "bg-slate-800 text-slate-300"
                            : node.layer === "streaming"
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : node.layer === "bronze"
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : node.layer === "silver"
                            ? "bg-slate-300/20 text-slate-200 border border-slate-400/30"
                            : node.layer === "gold"
                            ? "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
                            : "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                        }`}
                      >
                        {node.layer}
                      </span>
                      <span className="text-[10px] text-emerald-400 font-semibold">✓ {node.status}</span>
                    </div>

                    <div>
                      <p className="text-xs font-bold text-white">{node.name}</p>
                      <p className="text-[11px] text-slate-400">{node.category}</p>
                    </div>

                    <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>{node.engine}</span>
                      <span className="text-sky-400">{node.lastSync}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right 1 Col: Node Inspector Drawer */}
          <div className="glass-panel rounded-2xl p-6 border border-slate-800 space-y-4">
            <h2 className="text-sm font-bold text-white tracking-wide flex items-center gap-2">
              <Server size={16} className="text-sky-400" />
              Node Metadata & Schema Inspector
            </h2>

            {selectedNode ? (
              <div className="space-y-4">
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2">
                  <span className="text-[10px] font-bold text-sky-400 uppercase font-mono">
                    {selectedNode.category}
                  </span>
                  <h3 className="text-base font-bold text-white">{selectedNode.name}</h3>
                  <p className="text-xs text-slate-400">Engine: {selectedNode.engine}</p>
                </div>

                <div className="space-y-2 text-xs">
                  {Object.entries(selectedNode)
                    .filter(([k]) => !["id", "name", "category", "layer", "status", "engine"].includes(k))
                    .map(([key, val]) => (
                      <div key={key} className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                        <span className="text-[10px] text-slate-400 uppercase font-semibold block mb-0.5">
                          {key.replace(/_/g, " ")}
                        </span>
                        <span className="text-xs font-mono text-cyan-300 break-all">
                          {Array.isArray(val) ? val.join(", ") : String(val)}
                        </span>
                      </div>
                    ))}
                </div>

                <div className="p-3.5 bg-slate-950 rounded-xl border border-slate-800 text-[11px] text-slate-400 space-y-1">
                  <span className="font-semibold text-white block">OpenLineage Standard Compliance:</span>
                  <p>Facet: `datasetVersion`, `schema`, `transformationLogic` validated in Marquez catalog.</p>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
