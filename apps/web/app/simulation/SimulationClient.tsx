"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import Link from "next/link";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine, Cell } from "recharts";
import { FlaskConical, Play, CheckCircle2, AlertTriangle, TrendingUp, TrendingDown, ArrowRight } from "lucide-react";
import { cn } from "../components/utils";

type StrategyResult = {
  strategy: string;
  expected_recovery_paise: number;
  cost_paise: number;
  net_recovery_paise: number;
  cases_processed: number;
  vs_optimal_paise: number;
};

export function SimulationClient() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<StrategyResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/simulate/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_size: 100, budget_paise: 500000 }),
      });
      if (!res.ok) throw new Error(`Failed with status ${res.status}`);
      const data = await res.json();
      
      const sorted = data.results.sort((a: StrategyResult, b: StrategyResult) => {
        if (a.strategy === "RECOVERFLOW_OPTIMAL") return -1;
        if (b.strategy === "RECOVERFLOW_OPTIMAL") return 1;
        return b.net_recovery_paise - a.net_recovery_paise;
      });
      
      setResults(sorted);
    } catch (err: any) {
      setError(err.message || "An error occurred during simulation.");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(paise / 100);
  };

  const chartData = results?.map(r => ({
    name: r.strategy.replace(/_/g, ' '),
    "Net Recovery": r.net_recovery_paise / 100,
    "Cost": r.cost_paise / 100,
    "Expected Gross": r.expected_recovery_paise / 100,
    isOptimal: r.strategy === "RECOVERFLOW_OPTIMAL",
    raw: r
  })) || [];

  return (
    <div className="flex flex-col h-full gap-8">
      
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 bg-[#1e1b4b]/40 backdrop-blur-2xl p-6 rounded-2xl border border-white/10 shadow-2xl">
        <div className="flex gap-4 items-start">
          <div className="w-12 h-12 rounded-xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center shrink-0">
            <FlaskConical className="w-6 h-6 text-brand-400" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white/90">Dry-Run Simulation Parameters</h2>
            <div className="flex gap-4 mt-2">
              <div className="flex items-center gap-1.5 text-sm text-white/60">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Sample Size: <span className="text-white font-mono">100 Cases</span>
              </div>
              <div className="flex items-center gap-1.5 text-sm text-white/60">
                <span className="w-2 h-2 rounded-full bg-blue-500" /> Budget Cap: <span className="text-white font-mono">₹5,000</span>
              </div>
            </div>
          </div>
        </div>

        <button 
          onClick={runSimulation}
          disabled={loading}
          className="group relative flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-brand-500 to-[#d946ef] hover:from-brand-500/90 hover:to-[#d946ef]/90 text-white rounded-xl font-bold transition-all shadow-[0_0_20px_rgba(217,70,239,0.3)] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
          ) : (
            <Play className="w-5 h-5 fill-current group-hover:scale-110 transition-transform" />
          )}
          {loading ? "Running 100 Cases..." : "Run Strategy Comparison"}
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 flex items-center gap-3">
          <AlertTriangle className="w-5 h-5" />
          <strong>Simulation Failed:</strong> {error}
        </div>
      )}

      {/* Results View */}
      {results && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 min-h-0"
        >
          {/* Main Chart */}
          <div className="lg:col-span-2 bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-2xl flex flex-col">
            <h3 className="text-lg font-bold text-white/90 mb-6">Financial Impact Comparison</h3>
            <div className="flex-1 min-h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }} barGap={8}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                  <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12, fontWeight: 600 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `₹${v}`} />
                  <Tooltip
                    cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                    contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "12px", color: "#f1f5f9", boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)" }}
                    formatter={(value: number) => `₹${value.toLocaleString()}`}
                  />
                  <Legend wrapperStyle={{ paddingTop: '20px' }} />
                  
                  <Bar dataKey="Expected Gross" fill="#3b82f6" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="Cost" fill="#f43f5e" radius={[4, 4, 0, 0]} maxBarSize={40} />
                  <Bar dataKey="Net Recovery" radius={[4, 4, 0, 0]} maxBarSize={40}>
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.isOptimal ? "#10b981" : "#94a3b8"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Details Column */}
          <div className="space-y-4 flex flex-col h-full overflow-y-auto custom-scrollbar">
            {chartData.map((d, i) => (
              <div 
                key={d.name}
                className={cn(
                  "p-5 rounded-2xl border transition-colors",
                  d.isOptimal ? "bg-emerald-500/10 border-emerald-500/30" : "bg-black/20 border-white/5"
                )}
              >
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      {d.isOptimal && <CheckCircle2 className="w-4 h-4 text-emerald-400" />}
                      <h4 className={cn("font-bold", d.isOptimal ? "text-emerald-400" : "text-white/80")}>
                        {d.name}
                      </h4>
                    </div>
                    {d.isOptimal && <span className="text-[10px] uppercase tracking-wider bg-emerald-500/20 text-emerald-300 px-2 py-0.5 rounded font-bold">Recommended</span>}
                  </div>
                  <div className="text-right">
                    <div className="text-xl font-black text-white">{formatCurrency(d.raw.net_recovery_paise)}</div>
                    <div className="text-xs text-white/50">Net Recovery</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-black/20 p-2.5 rounded-lg border border-white/5">
                    <div className="text-xs text-white/40 mb-1">Cost Burn</div>
                    <div className="font-semibold text-rose-400">{formatCurrency(d.raw.cost_paise)}</div>
                  </div>
                  <div className="bg-black/20 p-2.5 rounded-lg border border-white/5">
                    <div className="text-xs text-white/40 mb-1">Expected Gross</div>
                    <div className="font-semibold text-blue-400">{formatCurrency(d.raw.expected_recovery_paise)}</div>
                  </div>
                </div>

                {!d.isOptimal && (
                  <div className="mt-3 flex items-center justify-between text-xs font-medium px-3 py-2 rounded-lg bg-white/5">
                    <span className="text-white/50">Opportunity Loss:</span>
                    <span className="text-rose-400 flex items-center gap-1">
                      <TrendingDown className="w-3 h-3" />
                      {formatCurrency(Math.abs(d.raw.vs_optimal_paise))}
                    </span>
                  </div>
                )}
                {d.isOptimal && (
                  <div className="mt-3 flex items-center justify-between text-xs font-bold px-3 py-2 rounded-lg bg-emerald-500/20 text-emerald-300">
                    <span>Highest Yield Achieved</span>
                    <TrendingUp className="w-3 h-3" />
                  </div>
                )}
              </div>
            ))}
          </div>

        </motion.div>
      )}

      {/* Empty State */}
      {!results && !loading && !error && (
        <div className="flex-1 flex items-center justify-center border-2 border-dashed border-white/10 rounded-2xl bg-white/[0.02]">
          <div className="text-center max-w-md p-6">
            <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center mx-auto mb-4 border border-white/10">
              <FlaskConical className="w-8 h-8 text-white/40" />
            </div>
            <h3 className="text-lg font-bold text-white/70 mb-2">Awaiting Simulation</h3>
            <p className="text-sm text-white/40 leading-relaxed">
              Run the dry-run simulator to process 100 historical payment failures against our ML-optimized policy versus legacy static rules.
            </p>
          </div>
        </div>
      )}

    </div>
  );
}
