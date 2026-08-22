"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";

export default function ReplayLabPage({ params }: { params: { id: string } }) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any>(null);
  const [strategy, setStrategy] = useState("RECOVERFLOW_OPTIMAL");
  const [error, setError] = useState<string | null>(null);

  const fetchReplay = async (selectedStrategy: string) => {
    setLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const res = await fetch(`${apiUrl}/simulate/replay/${params.id}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ strategy: selectedStrategy }),
      });
      if (res.status === 404) {
        notFound();
      }
      if (!res.ok) {
        throw new Error("Failed to run replay simulation");
      }
      const jsonData = await res.json();
      setData(jsonData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReplay(strategy);
  }, [params.id]);

  const handleRunReplay = () => {
    fetchReplay(strategy);
  };

  if (loading && !data) {
    return (
      <div className="min-h-screen bg-[#0b1326] text-white flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#06b6d4]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      {/* Background glow effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#06b6d4]/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href={`/cases/${params.id}`} className="text-white/40 hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
              </Link>
              <h1 className="text-2xl font-bold tracking-tight text-white/90 font-mono">Event Replay Lab</h1>
            </div>
            <p className="text-white/50 text-sm ml-8">Simulate counterfactual strategies for Case {params.id.split("-")[0]}</p>
          </div>
        </header>

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-lg">
            {error}
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            {/* Timeline Column */}
            <div className="lg:col-span-1 space-y-4">
              <h2 className="text-lg font-semibold text-white/80 border-b border-white/10 pb-2">Event Sequence</h2>
              <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 h-[600px] overflow-y-auto">
                <div className="space-y-6">
                  {data.timeline.map((event: any, idx: number) => (
                    <div key={event.id || idx} className="relative pl-6 border-l border-white/10 pb-2">
                      <div className={`absolute w-2 h-2 rounded-full -left-[4.5px] top-1.5 ${
                        event.type === 'FUNNEL' ? 'bg-purple-500 shadow-[0_0_8px_#a855f7]' :
                        event.type === 'PAYMENT_ATTEMPT' ? 'bg-red-500 shadow-[0_0_8px_#ef4444]' :
                        'bg-[#06b6d4] shadow-[0_0_8px_#06b6d4]'
                      }`} />
                      <div className="flex flex-col mb-1">
                        <span className="text-xs text-white/40">{new Date(event.timestamp).toLocaleString()}</span>
                        <h3 className="text-sm font-semibold text-white mt-1">{event.type}</h3>
                      </div>
                      <div className="text-sm text-white/70">
                        {event.description}
                      </div>
                    </div>
                  ))}
                  {data.timeline.length === 0 && (
                    <div className="text-white/40 text-sm italic">No timeline events found.</div>
                  )}
                </div>
              </div>
            </div>

            {/* Replay Controls & Comparison Column */}
            <div className="lg:col-span-2 space-y-6">
              
              {/* Controls */}
              <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6">
                <h2 className="text-lg font-semibold text-white/80 border-b border-white/10 pb-2 mb-4">Counterfactual Strategy</h2>
                <div className="flex items-end gap-4">
                  <div className="flex-1">
                    <label className="block text-xs text-white/50 mb-2 uppercase tracking-wider">Select Strategy</label>
                    <select 
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full bg-black/40 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#06b6d4]"
                    >
                      <option value="RECOVERFLOW_OPTIMAL">AI Optimal (Phase 8.5 Optimizer)</option>
                      <option value="REMINDER_ONLY">Static: Reminder Only</option>
                      <option value="DISCOUNT_5">Static: 5% Discount</option>
                      <option value="DISCOUNT_10">Static: 10% Discount</option>
                      <option value="RETRY_PLUS_REMINDER">Static: Retry + Reminder</option>
                      <option value="NO_ACTION">Static: Do Nothing</option>
                    </select>
                  </div>
                  <button 
                    onClick={handleRunReplay}
                    disabled={loading}
                    className="bg-[#06b6d4] hover:bg-[#0891b2] text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 flex items-center gap-2"
                  >
                    {loading ? (
                      <span className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></span>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    )}
                    Replay
                  </button>
                </div>
              </div>

              {/* Comparison */}
              <div className="grid grid-cols-2 gap-6">
                
                {/* Before */}
                <div className="bg-black/20 rounded-2xl border border-white/5 p-6">
                  <h3 className="text-sm font-medium text-white/50 uppercase tracking-wider mb-6">Actual Outcome</h3>
                  <div className="space-y-6">
                    <div>
                      <p className="text-xs text-white/40 mb-1">Action Executed</p>
                      <p className="text-lg font-mono text-white/80">{data.before.action_type}</p>
                    </div>
                    <div>
                      <p className="text-xs text-white/40 mb-1">Expected Recovery</p>
                      <p className="text-2xl font-bold text-white">₹{(data.before.expected_recovery_paise / 100).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-white/40 mb-1">Action Cost</p>
                      <p className="text-lg text-red-400">₹{(data.before.cost_paise / 100).toLocaleString()}</p>
                    </div>
                    <div className="pt-4 border-t border-white/10">
                      <p className="text-xs text-white/40 mb-1">Net Gain</p>
                      <p className="text-2xl font-bold text-[#06b6d4]">₹{(data.before.net_recovery_paise / 100).toLocaleString()}</p>
                    </div>
                  </div>
                </div>

                {/* After */}
                <div className="bg-[#1e1b4b]/60 backdrop-blur-2xl rounded-2xl border border-[#06b6d4]/30 p-6 relative overflow-hidden">
                  <div className="absolute top-0 right-0 p-4">
                    <span className="px-2 py-1 bg-[#06b6d4]/20 text-[#06b6d4] text-xs rounded uppercase font-bold tracking-wider">Simulated</span>
                  </div>
                  <h3 className="text-sm font-medium text-white/90 uppercase tracking-wider mb-6">Counterfactual Outcome</h3>
                  <div className="space-y-6 relative z-10">
                    <div>
                      <p className="text-xs text-[#06b6d4]/60 mb-1">Action Recommended</p>
                      <p className="text-lg font-mono text-white">{data.after.action_type}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#06b6d4]/60 mb-1">Expected Recovery</p>
                      <p className="text-2xl font-bold text-white">₹{(data.after.expected_recovery_paise / 100).toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#06b6d4]/60 mb-1">Action Cost</p>
                      <p className="text-lg text-red-400">₹{(data.after.cost_paise / 100).toLocaleString()}</p>
                    </div>
                    <div className="pt-4 border-t border-white/10">
                      <p className="text-xs text-[#06b6d4]/60 mb-1">Net Gain</p>
                      <p className="text-2xl font-bold text-[#06b6d4]">₹{(data.after.net_recovery_paise / 100).toLocaleString()}</p>
                    </div>
                  </div>
                </div>

              </div>

            </div>
          </div>
        )}

      </div>
    </div>
  );
}
