"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Play, FastForward, Activity, Sparkles, TrendingDown, TrendingUp, Cpu, XCircle } from "lucide-react";
import { cn } from "../../../components/utils";

const STRATEGIES_TO_COMPARE = [
  { id: "RECOVERFLOW_OPTIMAL", label: "AI Optimal", icon: Sparkles, color: "brand" },
  { id: "DISCOUNT_10", label: "Static: 10% Discount", icon: TrendingDown, color: "orange" },
  { id: "RETRY_PLUS_REMINDER", label: "Static: Retry", icon: Activity, color: "blue" },
];

export function ReplayClient({ caseId }: { caseId: string }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null); // To hold the timeline and actual outcome
  const [simulations, setSimulations] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);

  const fetchReplay = async () => {
    setLoading(true);
    setError(null);
    try {
      const results: Record<string, any> = {};
      let baseData: any = null;

      // Run multiple simulations in parallel
      await Promise.all(STRATEGIES_TO_COMPARE.map(async (strat) => {
        const res = await fetch(`/api/simulate/replay/${caseId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ strategy: strat.id }),
        });
        if (!res.ok) throw new Error(`Failed to replay ${strat.id}`);
        const json = await res.json();
        
        // Use the first successful response to capture the shared "timeline" and "before" state
        if (!baseData) baseData = json;
        
        results[strat.id] = json.after;
      }));

      setData(baseData);
      setSimulations(results);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReplay();
  }, [caseId]);

  const formatCurrency = (paise: number) => {
    return `₹${(paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
  };

  if (loading && !data) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <FastForward className="w-8 h-8 text-brand-500 animate-pulse" />
        <p className="text-white/50 text-sm animate-pulse">Running Counterfactual Scenarios...</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full gap-6">
      
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 flex items-center gap-3 shrink-0">
          <XCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {data && (
        <div className="flex-1 grid grid-cols-1 xl:grid-cols-4 gap-6 min-h-0">
          
          {/* Timeline Column */}
          <div className="xl:col-span-1 bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 flex flex-col overflow-hidden shadow-2xl relative">
            <div className="absolute inset-0 bg-gradient-to-b from-brand-500/5 to-transparent pointer-events-none" />
            <div className="p-4 border-b border-white/10 bg-black/20 flex items-center gap-2 relative z-10">
              <Activity className="w-4 h-4 text-brand-400" />
              <h2 className="text-sm font-semibold text-white/90">Actual Event Sequence</h2>
            </div>
            
            <div className="flex-1 overflow-y-auto p-4 custom-scrollbar relative z-10">
              <div className="space-y-6">
                {data.timeline.map((event: any, idx: number) => (
                  <motion.div 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: idx * 0.1 }}
                    key={event.id || idx} 
                    className="relative pl-6 border-l border-white/10 pb-2"
                  >
                    <div className={cn(
                      "absolute w-2 h-2 rounded-full -left-[4.5px] top-1.5",
                      event.type === 'FUNNEL' ? 'bg-purple-500 shadow-[0_0_8px_#a855f7]' :
                      event.type === 'PAYMENT_ATTEMPT' ? 'bg-rose-500 shadow-[0_0_8px_#ef4444]' :
                      'bg-[#06b6d4] shadow-[0_0_8px_#06b6d4]'
                    )} />
                    <div className="flex flex-col mb-1">
                      <span className="text-[10px] uppercase tracking-wider text-white/40">{new Date(event.timestamp).toLocaleString()}</span>
                      <h3 className="text-sm font-bold text-white mt-0.5">{event.type}</h3>
                    </div>
                    <div className="text-xs text-white/60 leading-relaxed mt-1">
                      {event.description}
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>

          {/* Comparison Column */}
          <div className="xl:col-span-3 space-y-6 flex flex-col min-h-0">
            
            {/* Action Bar */}
            <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-5 flex items-center justify-between shrink-0 shadow-2xl">
              <div>
                <h2 className="text-lg font-bold text-white/90">Multiverse Simulator</h2>
                <p className="text-sm text-white/50">Compare AI against static rulesets for this exact failure.</p>
              </div>
              <button 
                onClick={fetchReplay}
                disabled={loading}
                className="flex items-center gap-2 px-6 py-2.5 bg-brand-500/20 text-brand-300 hover:bg-brand-500/30 border border-brand-500/30 rounded-xl font-bold transition-all disabled:opacity-50"
              >
                {loading ? <Cpu className="w-4 h-4 animate-spin" /> : <FastForward className="w-4 h-4" />}
                Re-Run Simulation
              </button>
            </div>

            {/* Results Grid */}
            <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                
                {/* Actual Reality */}
                <div className="bg-black/30 rounded-2xl border border-white/10 p-6 flex flex-col justify-between group opacity-70 hover:opacity-100 transition-opacity">
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <h3 className="text-xs font-bold text-white/50 uppercase tracking-widest">Base Reality</h3>
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider bg-white/5 text-white/40 border border-white/10 uppercase">
                        What Happened
                      </span>
                    </div>
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs text-white/40 mb-1">Action Enacted</p>
                        <p className="text-base font-bold text-white/80">{data.before.action_type}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                          <p className="text-[10px] text-white/40 mb-1 uppercase tracking-wider">Gross Expected</p>
                          <p className="text-lg font-black text-white/70">{formatCurrency(data.before.expected_recovery_paise)}</p>
                        </div>
                        <div className="bg-white/5 p-3 rounded-xl border border-white/5">
                          <p className="text-[10px] text-white/40 mb-1 uppercase tracking-wider">Action Cost</p>
                          <p className="text-lg font-black text-rose-400/70">{formatCurrency(data.before.cost_paise)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div className="mt-6 pt-4 border-t border-white/10 flex justify-between items-end">
                    <p className="text-xs text-white/40 uppercase tracking-wider">Net Yield</p>
                    <p className="text-2xl font-black text-white/80">{formatCurrency(data.before.net_recovery_paise)}</p>
                  </div>
                </div>

                {/* Counterfactuals */}
                {STRATEGIES_TO_COMPARE.map((strat, idx) => {
                  const sim = simulations[strat.id];
                  if (!sim) return null;
                  
                  const isOptimal = strat.id === "RECOVERFLOW_OPTIMAL";
                  const colorMap: Record<string, { bg: string; border: string; text: string; highlight: string; accent: string; }> = {
                    brand: { bg: "bg-brand-500/10", border: "border-brand-500/30", text: "text-brand-400", highlight: "bg-brand-500/20 text-brand-300", accent: "text-brand-300" },
                    orange: { bg: "bg-orange-500/10", border: "border-orange-500/30", text: "text-orange-400", highlight: "bg-orange-500/20 text-orange-300", accent: "text-orange-300" },
                    blue: { bg: "bg-blue-500/10", border: "border-blue-500/30", text: "text-blue-400", highlight: "bg-blue-500/20 text-blue-300", accent: "text-blue-300" },
                  };
                  const colorConfig = colorMap[strat.color];

                  return (
                    <motion.div 
                      key={strat.id}
                      initial={{ opacity: 0, scale: 0.95 }}
                      animate={{ opacity: 1, scale: 1 }}
                      transition={{ delay: 0.2 + (idx * 0.1) }}
                      className={cn("rounded-2xl border p-6 flex flex-col justify-between relative overflow-hidden shadow-xl", colorConfig?.bg, colorConfig?.border)}
                    >
                      {isOptimal && <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-500/20 via-transparent to-transparent pointer-events-none" />}
                      
                      <div className="relative z-10">
                        <div className="flex items-center justify-between mb-6">
                          <h3 className={cn("text-xs font-bold uppercase tracking-widest flex items-center gap-1.5", colorConfig?.text)}>
                            <strat.icon className="w-3.5 h-3.5" />
                            {strat.label}
                          </h3>
                          <span className={cn("px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border border-current", colorConfig?.highlight)}>
                            Simulated
                          </span>
                        </div>
                        <div className="space-y-4">
                          <div>
                            <p className={cn("text-xs mb-1", colorConfig?.text, "opacity-70")}>Action Recommended</p>
                            <p className="text-base font-bold text-white">{sim.action_type}</p>
                          </div>
                          <div className="grid grid-cols-2 gap-4">
                            <div className="bg-black/20 p-3 rounded-xl border border-white/5">
                              <p className={cn("text-[10px] mb-1 uppercase tracking-wider", colorConfig?.text, "opacity-70")}>Gross Expected</p>
                              <p className="text-lg font-black text-white">{formatCurrency(sim.expected_recovery_paise)}</p>
                            </div>
                            <div className="bg-black/20 p-3 rounded-xl border border-white/5">
                              <p className={cn("text-[10px] mb-1 uppercase tracking-wider", colorConfig?.text, "opacity-70")}>Action Cost</p>
                              <p className="text-lg font-black text-rose-400">{formatCurrency(sim.cost_paise)}</p>
                            </div>
                          </div>
                        </div>
                      </div>
                      <div className="mt-6 pt-4 border-t border-white/10 flex justify-between items-end relative z-10">
                        <p className={cn("text-xs uppercase tracking-wider", colorConfig?.text, "opacity-70")}>Net Yield</p>
                        <p className={cn("text-3xl font-black", colorConfig?.accent)}>{formatCurrency(sim.net_recovery_paise)}</p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
