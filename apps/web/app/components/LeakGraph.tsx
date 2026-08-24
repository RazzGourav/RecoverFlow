"use client";

import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight, AlertTriangle, ArrowDownRight, Activity, X } from "lucide-react";
import Link from "next/link";
import { cn } from "./utils";

interface RootCauseBreakdown { failure_type: string; count: number; revenue_at_risk_paise: number; }
interface SegmentBreakdown { segment: string; count: number; }
interface RecoveryActionSummary { action_type: string; count: number; total_expected_recovery_paise: number; }

interface LeakPoint {
  from_stage: string;
  to_stage: string;
  lost_count: number;
  lost_value_paise: number;
  root_causes: RootCauseBreakdown[];
  affected_segments: SegmentBreakdown[];
  recovery_actions: RecoveryActionSummary[];
}

interface FunnelStage {
  stage: string;
  count: number;
  value_paise: number;
  data_source: "simulated" | "live";
}

export interface LeakGraphData {
  stages: FunnelStage[];
  leaks: LeakPoint[];
  generated_at: string;
  note: string;
}

const STAGE_LABELS: Record<string, string> = {
  SITE_VISIT: "Site Visits",
  PRODUCT_VIEW: "Product Views",
  ADD_TO_CART: "Add to Cart",
  CHECKOUT_STARTED: "Checkout",
  PAYMENT_ATTEMPTED: "Payment Attempts",
  PAYMENT_SUCCESSFUL: "Successful",
};

const STAGE_COLORS: Record<string, string> = {
  SITE_VISIT: "#6366f1",
  PRODUCT_VIEW: "#8b5cf6",
  ADD_TO_CART: "#a78bfa",
  CHECKOUT_STARTED: "#f59e0b",
  PAYMENT_ATTEMPTED: "#ef4444",
  PAYMENT_SUCCESSFUL: "#10b981",
};

function formatPaise(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(2)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

export function LeakGraph({ initialData }: { initialData?: LeakGraphData | null } = {}) {
  const [data, setData] = useState<LeakGraphData | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const [selectedLeak, setSelectedLeak] = useState<LeakPoint | null>(null);

  useEffect(() => {
    if (initialData) return;
    fetch("/api/leak-graph")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d: LeakGraphData) => {
        setData(d);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, [initialData]);

  if (loading || !data) return null;

  const chartData = data.stages.map((s) => ({
    name: STAGE_LABELS[s.stage] || s.stage,
    count: s.count,
    value: s.value_paise,
    stage: s.stage,
    source: s.data_source,
  }));

  return (
    <div className="space-y-6">
      
      {/* Honesty Badges Legend */}
      <div className="flex gap-4 justify-end mb-4">
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 border border-white/10 text-xs text-white/50">
          <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse" />
          Simulated Traffic Data (Demo)
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/5 border border-white/10 text-xs text-white/50">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Live System Data
        </div>
      </div>

      <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-2xl">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: 'rgba(255,255,255,0.05)' }}
              contentStyle={{ backgroundColor: "#0f172a", border: "1px solid #334155", borderRadius: "12px", color: "#f1f5f9", boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)" }}
              formatter={(value: number, name: string) => [formatCount(value), name === "count" ? "Sessions" : "Value"]}
            />
            <Bar dataKey="count" radius={[8, 8, 0, 0]} maxBarSize={60}>
              {chartData.map((entry, idx) => (
                <Cell key={`cell-${idx}`} fill={STAGE_COLORS[entry.stage] || "#6366f1"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        {data.stages.map((stage, idx) => {
          const leak = data.leaks.find((l) => l.from_stage === stage.stage);
          const dropRate = idx > 0 && data.stages[idx - 1].count > 0 ? (((data.stages[idx - 1].count - stage.count) / data.stages[idx - 1].count) * 100).toFixed(1) : null;
          const isLive = stage.data_source === 'live';

          return (
            <div key={stage.stage} className="bg-black/20 rounded-xl p-4 border border-white/5 relative overflow-hidden group">
              <div className={cn("absolute top-0 left-0 w-full h-1", `bg-[${STAGE_COLORS[stage.stage]}]`)} style={{ backgroundColor: STAGE_COLORS[stage.stage] }} />
              
              <div className="flex justify-between items-start mb-4">
                <h3 className="text-xs font-bold text-white/80">{STAGE_LABELS[stage.stage] || stage.stage}</h3>
                <div className={cn("w-2 h-2 rounded-full", isLive ? "bg-emerald-500 shadow-[0_0_8px_#10b981]" : "bg-purple-500 shadow-[0_0_8px_#a855f7]")} title={isLive ? "Live Data" : "Simulated"} />
              </div>

              <div className="text-xl font-black text-white tracking-tight">{formatCount(stage.count)}</div>
              <div className="text-[10px] text-white/40 uppercase tracking-widest mt-1 mb-4">{formatPaise(stage.value_paise)} Value</div>

              {dropRate && (
                <div className="text-[10px] font-bold text-rose-400 flex items-center gap-1 bg-rose-500/10 px-2 py-1 rounded w-max mb-2">
                  <ArrowDownRight className="w-3 h-3" /> {dropRate}% drop
                </div>
              )}

              {leak && leak.lost_count > 0 && (
                <button
                  onClick={() => setSelectedLeak(leak)}
                  className="mt-2 w-full text-[10px] font-bold uppercase tracking-wider px-2 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-colors flex items-center justify-between"
                >
                  Analyze Leak <Activity className="w-3 h-3" />
                </button>
              )}
            </div>
          );
        })}
      </div>

      <AnimatePresence>
        {selectedLeak && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-[#1e1b4b]/60 backdrop-blur-3xl p-6 rounded-2xl border-l-4 border-l-rose-500 border border-white/10 shadow-2xl mt-4">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h3 className="text-lg font-bold text-white/90 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5 text-rose-400" />
                    Leak Point: {STAGE_LABELS[selectedLeak.from_stage]} → {STAGE_LABELS[selectedLeak.to_stage]}
                  </h3>
                </div>
                <button onClick={() => setSelectedLeak(null)} className="p-2 hover:bg-white/10 rounded-full transition-colors text-white/50">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                
                <div className="bg-black/20 p-4 rounded-xl border border-white/5">
                  <div className="text-white/40 mb-1 uppercase text-xs font-bold tracking-wider">Lost Sessions</div>
                  <div className="text-3xl font-black text-rose-400">{formatCount(selectedLeak.lost_count)}</div>
                  <div className="text-rose-400/60 text-sm font-medium mt-1">{formatPaise(selectedLeak.lost_value_paise)} at risk</div>
                  
                  <Link href="/cases?filter=blocked" className="mt-6 flex items-center gap-2 text-xs font-bold bg-brand-500/20 text-brand-300 hover:bg-brand-500/30 px-3 py-2 rounded-lg transition-colors justify-center w-full">
                    View Impacted Cases <ArrowRight className="w-3 h-3" />
                  </Link>
                </div>

                {selectedLeak.root_causes.length > 0 && (
                  <div className="bg-black/20 p-4 rounded-xl border border-white/5 md:col-span-1">
                    <div className="text-white/40 mb-3 uppercase text-xs font-bold tracking-wider">Root Causes</div>
                    <div className="space-y-2">
                      {selectedLeak.root_causes.map((rc) => (
                        <div key={rc.failure_type} className="flex justify-between items-center bg-white/5 px-2 py-1.5 rounded">
                          <span className="text-xs text-white/70">{rc.failure_type}</span>
                          <span className="text-xs font-bold text-white/90">{rc.count}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {selectedLeak.recovery_actions.length > 0 && (
                  <div className="bg-black/20 p-4 rounded-xl border border-white/5 md:col-span-2">
                    <div className="text-white/40 mb-3 uppercase text-xs font-bold tracking-wider">AI Recovery Strategies Enacted</div>
                    <div className="space-y-2">
                      {selectedLeak.recovery_actions.map((ra) => (
                        <div key={ra.action_type} className="flex justify-between items-center bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 rounded-lg">
                          <span className="text-xs font-medium text-emerald-400">{ra.action_type}</span>
                          <span className="text-xs font-bold text-emerald-400 flex items-center gap-2">
                            {ra.count} Executed
                            <span className="bg-emerald-500/20 px-2 py-0.5 rounded text-emerald-300">
                              {formatPaise(ra.total_expected_recovery_paise)} EV
                            </span>
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

    </div>
  );
}
