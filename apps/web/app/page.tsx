import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { LeakGraph } from "./components/LeakGraph";

export const metadata: Metadata = {
  title: "Revenue Control Tower | RecoverFlow",
  description: "AI Revenue Recovery Control Plane dashboard.",
};

async function getMetrics() {
  try {
    const res = await fetch("http://api:8000/metrics", { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}

async function getFeed() {
  try {
    const res = await fetch("http://api:8000/dashboard/feed", { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}

// Re-use the existing leak graph data fetching logic so we can embed the leak graph directly
async function getLeakGraphData() {
  try {
    const res = await fetch("http://api:8000/leak-graph", { cache: "no-store" });
    if (!res.ok) return null;
    return res.json();
  } catch (e) {
    return null;
  }
}

export default async function RevenueControlTower() {
  const [metrics, feed, leakData] = await Promise.all([
    getMetrics(),
    getFeed(),
    getLeakGraphData()
  ]);

  const recentCases = feed?.recent_cases || [];
  const highRiskAlerts = feed?.high_risk_alerts || [];

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      {/* Background glow effects for glassmorphism */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#581c87]/20 rounded-full blur-[100px]" />
        <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[#0f172a]/40 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white/90">Revenue Control Tower</h1>
            <p className="text-white/50 text-sm mt-1">Live monitoring and autonomous action command center.</p>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/cases" className="text-sm font-medium text-brand-300 hover:text-brand-200 bg-brand-900/30 border border-brand-500/20 px-4 py-2 rounded-lg backdrop-blur-md transition-colors">
              View All Cases
            </Link>
            <Link href="/simulation" className="text-sm font-medium text-[#d946ef] hover:text-[#f0abfc] bg-[#d946ef]/10 border border-[#d946ef]/30 px-4 py-2 rounded-lg backdrop-blur-md transition-colors">
              Simulation Lab
            </Link>
            <Link href="/policies" className="text-sm font-medium text-white hover:text-brand-100 bg-[#06b6d4]/20 border border-[#06b6d4]/40 px-4 py-2 rounded-lg backdrop-blur-md transition-colors">
              Policy Studio
            </Link>
          </div>
        </header>

        {/* Top Metrics Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <MetricCard 
            title="Incremental Recovered"
            value={metrics ? `₹${(metrics.incremental_recovered_revenue_paise / 100).toLocaleString()}` : "—"}
            color="text-[#06b6d4]"
          />
          <MetricCard 
            title="Recovery Rate"
            value={metrics ? `${metrics.recovery_rate_percent}%` : "—"}
            color="text-[#d946ef]"
          />
          <MetricCard 
            title="Reconciliation Exceptions"
            value={metrics ? `${metrics.reconciliation_exception_rate_percent}%` : "—"}
            color="text-white"
          />
        </div>

        {/* Funnel Graph Section */}
        <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-2xl">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold text-white/80">Revenue Leak Funnel</h2>
            <Link href="/leak-graph" className="text-xs text-[#06b6d4] hover:underline">Expand View</Link>
          </div>
          {leakData ? (
             <LeakGraph initialData={leakData} />
          ) : (
            <div className="h-64 flex items-center justify-center text-white/40">No funnel data available</div>
          )}
        </section>

        {/* Two-column Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Recent Cases */}
          <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-2xl flex flex-col h-[400px]">
            <h2 className="text-lg font-semibold text-white/80 mb-4 flex items-center justify-between">
              Recent Cases
              <span className="text-xs font-normal text-white/40 px-2 py-1 rounded bg-white/5">{recentCases.length} records</span>
            </h2>
            <div className="overflow-y-auto flex-1 pr-2 space-y-3 custom-scrollbar">
              {recentCases.map((c: any) => (
                <Link href={`/cases/${c.id}`} key={c.id} className="block bg-black/20 hover:bg-black/40 border border-white/5 rounded-xl p-4 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium text-white/70 truncate mr-4">{c.id.split("-")[0]}...</span>
                    <span className="text-sm font-semibold text-white">₹{(c.amount_paise / 100).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className={`px-2 py-0.5 rounded-full ${getStatusColor(c.status)}`}>
                      {c.status}
                    </span>
                    <span className="text-white/40">{new Date(c.created_at).toLocaleTimeString()}</span>
                  </div>
                </Link>
              ))}
              {recentCases.length === 0 && (
                <div className="text-center text-white/40 py-8 text-sm">No recent cases found.</div>
              )}
            </div>
          </section>

          {/* High-Risk Alerts */}
          <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-[#d946ef]/20 p-6 shadow-2xl flex flex-col h-[400px] relative overflow-hidden">
            {/* Subtle alert pulsing background */}
            <div className="absolute top-0 right-0 w-[300px] h-[300px] bg-[#d946ef]/5 rounded-full blur-[80px] animate-pulse pointer-events-none" />
            
            <h2 className="text-lg font-semibold text-[#d946ef] mb-4 flex items-center justify-between relative z-10">
              <span className="flex items-center gap-2">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#d946ef] opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#d946ef]"></span>
                </span>
                High-Risk Alerts
              </span>
              <span className="text-xs font-normal text-white/40 px-2 py-1 rounded bg-white/5">{highRiskAlerts.length} active</span>
            </h2>
            <div className="overflow-y-auto flex-1 pr-2 space-y-3 custom-scrollbar relative z-10">
              {highRiskAlerts.map((c: any) => (
                <Link href={`/cases/${c.id}`} key={c.id} className="block bg-black/20 hover:bg-[#d946ef]/10 border border-[#d946ef]/20 rounded-xl p-4 transition-colors">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-sm font-medium text-white/90 truncate mr-4">Action Required</span>
                    <span className="text-sm font-semibold text-[#d946ef]">₹{(c.amount_paise / 100).toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between items-center text-xs">
                    <span className="text-white/60">Risk Level: HIGH</span>
                    <span className="text-white/40">{new Date(c.created_at).toLocaleTimeString()}</span>
                  </div>
                </Link>
              ))}
              {highRiskAlerts.length === 0 && (
                <div className="text-center text-white/40 py-8 text-sm">No high-risk alerts currently active.</div>
              )}
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}

function MetricCard({ title, value, color }: { title: string; value: string; color: string }) {
  return (
    <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 shadow-2xl flex flex-col justify-center min-h-[140px] hover:border-white/20 transition-all">
      <h3 className="text-sm font-medium text-white/50 mb-2">{title}</h3>
      <div className={`text-4xl font-bold tracking-tight ${color} filter drop-shadow-[0_0_10px_rgba(255,255,255,0.1)]`}>
        {value}
      </div>
    </div>
  );
}

function getStatusColor(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-[#06b6d4]/20 text-[#06b6d4] border border-[#06b6d4]/30';
    case 'PENDING': return 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30';
    case 'FAILED': return 'bg-red-500/20 text-red-300 border border-red-500/30';
    default: return 'bg-white/10 text-white/60 border border-white/20';
  }
}
