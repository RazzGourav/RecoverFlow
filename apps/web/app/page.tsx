"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { LeakGraph } from "./components/LeakGraph";
import { AlertCircle, ArrowUpRight, CheckCircle2, CircleDollarSign, Loader2, RefreshCcw, ShieldAlert } from "lucide-react";

function formatCurrency(paise: number) {
  return `₹${(paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
}

export default function RevenueControlTower() {
  const [metrics, setMetrics] = useState<any>(null);
  const [feed, setFeed] = useState<any>(null);
  const [leakData, setLeakData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [mRes, fRes, lRes] = await Promise.all([
          fetch("/api/metrics"),
          fetch("/api/dashboard/feed"),
          fetch("/api/leak-graph")
        ]);
        
        if (mRes.ok) setMetrics(await mRes.json());
        if (fRes.ok) setFeed(await fRes.json());
        if (lRes.ok) setLeakData(await lRes.json());
      } catch (e) {
        console.error("Failed to fetch dashboard data", e);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
    const interval = setInterval(fetchData, 5000); // Live update every 5s
    return () => clearInterval(interval);
  }, []);

  const recentCases = feed?.recent_cases || [];
  const highRiskAlerts = feed?.high_risk_alerts || [];

  if (loading && !metrics) {
    return (
      <div className="flex-1 flex items-center justify-center h-full min-h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full">
      {/* Header */}
      <header className="flex items-center justify-between mb-8">
        <motion.div 
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-3xl font-bold tracking-tight text-white/90">Revenue Control Tower</h1>
          <p className="text-white/50 text-sm mt-1">Live monitoring and autonomous action command center.</p>
        </motion.div>
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          className="flex items-center gap-2 bg-[#1e1b4b]/60 backdrop-blur-xl border border-brand-500/30 px-3 py-1.5 rounded-full"
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
          </span>
          <span className="text-xs font-medium text-emerald-400">System Online</span>
        </motion.div>
      </header>

      {/* Top Metrics Row */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8"
      >
        <MetricCard 
          title="Revenue at Risk"
          value={metrics ? formatCurrency(metrics.total_revenue_at_risk_paise || 0) : "—"}
          icon={<AlertCircle className="w-4 h-4 text-rose-400" />}
          color="text-rose-400"
          bgGlow="bg-rose-500/10"
        />
        <MetricCard 
          title="Recovered this Period"
          value={metrics ? formatCurrency(metrics.incremental_recovered_revenue_paise) : "—"}
          icon={<ArrowUpRight className="w-4 h-4 text-emerald-400" />}
          color="text-emerald-400"
          bgGlow="bg-emerald-500/10"
        />
        <MetricCard 
          title="Active Cases"
          value={metrics ? metrics.active_cases : "—"}
          icon={<RefreshCcw className="w-4 h-4 text-brand-400" />}
          color="text-brand-400"
          bgGlow="bg-brand-500/10"
        />
        <MetricCard 
          title="Budget Remaining"
          value={metrics ? formatCurrency(metrics.budget_remaining_paise || 0) : "—"}
          icon={<CircleDollarSign className="w-4 h-4 text-[#d946ef]" />}
          color="text-[#d946ef]"
          bgGlow="bg-[#d946ef]/10"
        />
      </motion.div>

      {/* Risk Alert Banner */}
      <AnimatePresence>
        {highRiskAlerts.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, height: 0, marginBottom: 0 }}
            animate={{ opacity: 1, height: 'auto', marginBottom: 32 }}
            exit={{ opacity: 0, height: 0, marginBottom: 0 }}
            className="overflow-hidden"
          >
            <div className="bg-rose-500/10 border border-rose-500/30 rounded-xl p-4 flex items-center justify-between backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-rose-500/20 flex items-center justify-center">
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                </div>
                <div>
                  <h4 className="text-sm font-semibold text-rose-400">Risk Firewall Engaged</h4>
                  <p className="text-xs text-rose-300/70">{highRiskAlerts.length} cases actively blocked and requiring human review.</p>
                </div>
              </div>
              <Link href="/cases?filter=blocked" className="text-xs font-medium bg-rose-500/20 text-rose-300 px-3 py-1.5 rounded-lg hover:bg-rose-500/30 transition-colors">
                Review Cases
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Funnel Graph */}
        <motion.section 
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="lg:col-span-2 bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 p-6 shadow-2xl relative overflow-hidden group"
        >
          <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-brand-500/5 rounded-full blur-[100px] pointer-events-none group-hover:bg-brand-500/10 transition-colors duration-700" />
          
          <div className="flex items-center justify-between mb-6 relative z-10">
            <div>
              <h2 className="text-lg font-semibold text-white/90">Revenue Leak Funnel</h2>
              <p className="text-xs text-white/40">End-to-end recovery conversion visibility</p>
            </div>
            <Link href="/leak-graph" className="text-xs font-medium text-brand-400 hover:text-brand-300 flex items-center gap-1 bg-brand-500/10 px-3 py-1.5 rounded-lg transition-colors">
              Deep Dive <ArrowUpRight className="w-3 h-3" />
            </Link>
          </div>
          {leakData ? (
             <LeakGraph initialData={leakData} />
          ) : (
            <div className="h-64 flex items-center justify-center text-white/40">No funnel data available</div>
          )}
        </motion.section>

        {/* Right Column: Live Feed */}
        <motion.section 
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 p-6 shadow-2xl flex flex-col h-[600px] relative"
        >
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white/90 flex items-center gap-2">
                Live Case Feed
              </h2>
              <p className="text-xs text-white/40">Real-time intervention tracker</p>
            </div>
            <div className="flex gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '0ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-bounce" style={{ animationDelay: '300ms' }} />
            </div>
          </div>
          
          <div className="overflow-y-auto flex-1 pr-2 space-y-3 custom-scrollbar">
            <AnimatePresence initial={false}>
              {recentCases.map((c: any) => (
                <motion.div
                  key={c.id}
                  initial={{ opacity: 0, y: -20, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  layout
                  className="block group"
                >
                  <Link href={`/cases/${c.id}`} className="block bg-white/[0.02] hover:bg-white/[0.06] border border-white/5 rounded-xl p-4 transition-all hover:border-brand-500/30">
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {c.status === 'RECOVERED' ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                        ) : c.status === 'FAILED' || c.status === 'UNRECOVERABLE' ? (
                          <AlertCircle className="w-4 h-4 text-rose-400" />
                        ) : (
                          <RefreshCcw className="w-4 h-4 text-brand-400" />
                        )}
                        <span className="text-sm font-medium text-white/80 group-hover:text-white transition-colors">
                          {c.id.split("-")[0]}
                        </span>
                      </div>
                      <span className="text-sm font-bold text-white tracking-tight">{formatCurrency(c.amount_paise)}</span>
                    </div>
                    <div className="flex justify-between items-center mt-3">
                      <span className={cn("px-2 py-0.5 rounded-md text-[10px] font-medium border", getStatusColor(c.status))}>
                        {c.status}
                      </span>
                      <span className="text-[11px] text-white/40 font-medium">
                        {new Date(c.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                  </Link>
                </motion.div>
              ))}
            </AnimatePresence>
            {recentCases.length === 0 && (
              <div className="h-full flex items-center justify-center text-sm text-white/30">
                Awaiting events...
              </div>
            )}
          </div>
        </motion.section>

      </div>
    </div>
  );
}

function MetricCard({ title, value, icon, color, bgGlow }: { title: string; value: string | number; icon: React.ReactNode; color: string; bgGlow: string }) {
  return (
    <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 p-5 shadow-2xl relative overflow-hidden group hover:border-white/10 transition-colors">
      <div className={cn("absolute -right-4 -top-4 w-24 h-24 rounded-full blur-[40px] pointer-events-none opacity-50 transition-opacity group-hover:opacity-100", bgGlow)} />
      <div className="flex items-center justify-between mb-3 relative z-10">
        <h3 className="text-xs font-medium text-white/50 uppercase tracking-wider">{title}</h3>
        <div className={cn("p-1.5 rounded-lg bg-white/5", color)}>
          {icon}
        </div>
      </div>
      <div className={cn("text-3xl font-bold tracking-tight relative z-10", color)}>
        {value}
      </div>
    </div>
  );
}

function getStatusColor(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    case 'PENDING': 
    case 'EXECUTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20';
    case 'HUMAN_REVIEW': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
    case 'FAILED': 
    case 'UNRECOVERABLE': return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    default: return 'bg-white/5 text-white/60 border-white/10';
  }
}

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
