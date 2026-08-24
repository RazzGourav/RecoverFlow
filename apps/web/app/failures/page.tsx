"use client";

import { useEffect, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { fetchAuditFailures } from "./actions";
import { ShieldAlert, AlertOctagon, TerminalSquare, Activity, RefreshCcw, Siren } from "lucide-react";
import { cn } from "../components/utils";

export default function FailuresPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const loadFailures = async () => {
    setLoading(true);
    try {
      const data = await fetchAuditFailures();
      setEvents(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load failures");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFailures();
  }, []);

  const handleTriggerIncident = async () => {
    setTriggering(true);
    try {
      const res = await fetch("/api/audit/trigger-incident", {
        method: "POST"
      });
      if (!res.ok) throw new Error("Failed to trigger incident");
      
      // Wait a moment for background script to generate records
      setTimeout(() => {
        loadFailures();
        setTriggering(false);
      }, 2000);

    } catch (e: any) {
      setError(e.message);
      setTriggering(false);
    }
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full h-[calc(100vh-2rem)] flex flex-col">
      <header className="mb-8 shrink-0 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white/90">Failure Center</h1>
          <p className="text-white/50 text-sm mt-1">Real-time monitoring of idempotency drops, stale states, and blocked webhooks.</p>
        </div>
        
        <div className="flex gap-4">
          <button 
            onClick={loadFailures}
            className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-white/60 hover:text-white hover:bg-white/10 flex items-center gap-2 text-sm font-medium transition-colors"
          >
            <RefreshCcw className={cn("w-4 h-4", loading && "animate-spin")} />
            Refresh
          </button>
          
          <button 
            onClick={handleTriggerIncident}
            disabled={triggering}
            className="group relative flex items-center gap-2 px-6 py-2 bg-rose-500/20 hover:bg-rose-500/30 text-rose-400 border border-rose-500/50 rounded-xl font-bold transition-all shadow-[0_0_15px_rgba(244,63,94,0.2)] hover:shadow-[0_0_25px_rgba(244,63,94,0.4)] disabled:opacity-50"
          >
            {triggering ? (
              <Activity className="w-5 h-5 animate-pulse" />
            ) : (
              <Siren className="w-5 h-5 fill-current group-hover:scale-110 transition-transform" />
            )}
            {triggering ? "Injecting Failures..." : "Simulate 2AM Incident"}
          </button>
        </div>
      </header>

      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 flex items-center gap-3 shrink-0 mb-6">
          <AlertOctagon className="w-5 h-5" />
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="flex-1 bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 shadow-2xl flex flex-col min-h-0 overflow-hidden relative">
        
        <div className="p-4 border-b border-white/10 bg-black/20 flex items-center justify-between z-10 relative">
          <div className="flex items-center gap-2">
            <TerminalSquare className="w-5 h-5 text-rose-400" />
            <h2 className="text-sm font-bold text-white/80 tracking-widest uppercase">System Dropped Events Log</h2>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/20">
            <div className="w-2 h-2 rounded-full bg-rose-500 animate-pulse" />
            <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">Live Monitoring</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar relative z-10 p-4">
          <div className="space-y-3">
            {events.length === 0 && !loading ? (
              <div className="h-64 flex flex-col items-center justify-center text-white/30 text-center">
                <ShieldAlert className="w-16 h-16 opacity-20 mb-4" />
                <h3 className="text-lg font-bold text-white/50 mb-1">System is Stable</h3>
                <p className="text-sm">No idempotency drops or validation failures detected.</p>
                <p className="text-xs mt-4 italic">Click "Simulate 2AM Incident" to test the safety net.</p>
              </div>
            ) : (
              events.map((evt) => (
                <div key={evt.id} className="bg-black/40 rounded-xl border border-rose-500/10 p-4 hover:border-rose-500/30 transition-colors flex gap-6">
                  
                  <div className="shrink-0 w-32">
                    <p className="text-xs font-mono text-white/40 mb-1">
                      {formatDistanceToNow(new Date(evt.timestamp), { addSuffix: true })}
                    </p>
                    <span className="inline-flex items-center rounded-md bg-rose-500/10 px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-rose-400 border border-rose-500/20">
                      {evt.event_type}
                    </span>
                  </div>

                  <div className="flex-1">
                    <p className="text-sm font-medium text-white/90 mb-2">
                      {evt.reason || "System dropped event."}
                    </p>
                    {evt.context && (
                      <div className="bg-[#0b1326] p-3 rounded-lg border border-white/5">
                        <pre className="text-[10px] text-brand-300 font-mono whitespace-pre-wrap overflow-x-auto">
                          {JSON.stringify(evt.context, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>

                  {evt.case_id && (
                    <div className="shrink-0">
                      <p className="text-[10px] text-white/40 uppercase tracking-wider mb-1 text-right">Target Case</p>
                      <span className="font-mono text-xs text-white/80 bg-white/5 px-2 py-1 rounded">
                        {evt.case_id.split("-")[0]}
                      </span>
                    </div>
                  )}

                </div>
              ))
            )}
          </div>
        </div>

      </div>

    </div>
  );
}
