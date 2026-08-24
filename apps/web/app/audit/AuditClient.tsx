"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import { Search, ShieldCheck, Cpu, Code2, Clock, Filter, AlertTriangle, ArrowRight, Zap, RefreshCcw } from "lucide-react";
import { cn } from "../components/utils";

export function AuditClient({ initialEvents }: { initialEvents: any[] }) {
  const [filter, setFilter] = useState("ALL");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const filteredEvents = initialEvents.filter(ae => {
    if (filter === "ALL") return true;
    if (filter === "POLICY") return ae.event_type.includes("POLICY");
    if (filter === "RISK") return ae.event_type.includes("RISK");
    if (filter === "ACTION") return ae.event_type.includes("ACTION");
    if (filter === "RECONCILIATION") return ae.event_type.includes("RECONCILIATION");
    return true;
  });

  const selectedEvent = initialEvents.find(e => e.id === selectedEventId);

  const filters = [
    { id: "ALL", label: "All Events" },
    { id: "POLICY", label: "Policy Checks" },
    { id: "RISK", label: "Risk Evaluations" },
    { id: "ACTION", label: "Actions Executed" },
    { id: "RECONCILIATION", label: "Reconciliations" },
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      
      {/* Filters */}
      <div className="flex gap-2 mb-6">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 flex items-center gap-2 border",
              filter === f.id
                ? "bg-brand-500/20 border-brand-500/40 text-brand-300 shadow-[0_0_15px_rgba(217,70,239,0.2)]"
                : "bg-white/5 border-white/10 text-white/60 hover:text-white/90 hover:bg-white/10"
            )}
          >
            <Filter className="w-4 h-4 opacity-50" />
            {f.label}
          </button>
        ))}
      </div>

      <div className="flex-1 flex gap-6 min-h-0">
        
        {/* Timeline List */}
        <div className="w-1/2 md:w-2/3 bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 overflow-hidden shadow-2xl flex flex-col">
          <div className="p-4 border-b border-white/10 bg-black/20 flex justify-between items-center">
            <h2 className="text-sm font-semibold text-white/80">Event Timeline</h2>
            <span className="text-xs text-white/40">{filteredEvents.length} records</span>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
            <div className="space-y-3">
              <AnimatePresence initial={false}>
                {filteredEvents.map((ae) => {
                  const isSelected = selectedEventId === ae.id;
                  const typeStyles = getTypeStyles(ae.event_type);
                  
                  return (
                    <motion.div
                      key={ae.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      onClick={() => setSelectedEventId(ae.id)}
                      className={cn(
                        "p-4 rounded-xl border transition-all cursor-pointer group relative overflow-hidden",
                        isSelected 
                          ? `bg-brand-500/10 border-brand-500/50 shadow-[0_0_20px_rgba(217,70,239,0.15)]` 
                          : "bg-black/20 border-white/5 hover:border-white/20 hover:bg-white/[0.04]"
                      )}
                    >
                      {isSelected && (
                        <motion.div layoutId="active-audit-border" className="absolute left-0 top-0 bottom-0 w-1 bg-brand-500" />
                      )}
                      
                      <div className="flex justify-between items-start mb-2 relative z-10">
                        <div className="flex items-center gap-2">
                          <span className={cn("p-1.5 rounded-lg border", typeStyles.bg, typeStyles.color, typeStyles.border)}>
                            <typeStyles.icon className="w-3.5 h-3.5" />
                          </span>
                          <span className="font-semibold text-white/90">{ae.event_type}</span>
                        </div>
                        <span className="text-xs text-white/40 flex items-center gap-1 font-mono">
                          <Clock className="w-3 h-3" />
                          {new Date(ae.timestamp).toLocaleTimeString([], { hour12: false })}
                        </span>
                      </div>
                      
                      <div className="pl-9 relative z-10">
                        <p className="text-sm text-white/70 line-clamp-1">{ae.reason || "No reason provided"}</p>
                        <div className="flex items-center gap-4 mt-3">
                          {ae.case_id && (
                            <span className="text-xs font-mono text-brand-400 bg-brand-500/10 px-2 py-0.5 rounded">
                              {ae.case_id.split("-")[0]}
                            </span>
                          )}
                          {ae.decision && (
                            <span className={cn(
                              "text-xs font-bold px-2 py-0.5 rounded uppercase tracking-wider",
                              ae.decision === 'ALLOW' ? 'text-emerald-400 bg-emerald-500/10' : 
                              ae.decision === 'BLOCK' ? 'text-rose-400 bg-rose-500/10' : 'text-orange-400 bg-orange-500/10'
                            )}>
                              {ae.decision}
                            </span>
                          )}
                        </div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              {filteredEvents.length === 0 && (
                <div className="h-40 flex flex-col items-center justify-center text-white/30 gap-2">
                  <Search className="w-8 h-8 opacity-50" />
                  <p>No events found for this filter.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Detail Panel */}
        <div className="w-1/2 md:w-1/3 bg-[#1e1b4b]/60 backdrop-blur-2xl rounded-2xl border border-brand-500/20 overflow-hidden shadow-2xl flex flex-col relative">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-brand-500/10 via-transparent to-transparent pointer-events-none" />
          
          <div className="p-4 border-b border-brand-500/20 bg-brand-500/5 flex items-center gap-2 relative z-10">
            <ShieldCheck className="w-5 h-5 text-brand-400" />
            <h2 className="text-sm font-semibold text-white/90">Execution Trace</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-6 relative z-10">
            <AnimatePresence mode="wait">
              {selectedEvent ? (
                <motion.div
                  key={selectedEvent.id}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-6"
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className={cn("px-2.5 py-1 rounded-md text-xs font-bold tracking-wider", getTypeStyles(selectedEvent.event_type).bg, getTypeStyles(selectedEvent.event_type).color)}>
                        {selectedEvent.event_type}
                      </span>
                      <span className="text-xs text-white/40">{new Date(selectedEvent.timestamp).toLocaleString()}</span>
                    </div>
                    <h3 className="text-lg font-semibold text-white/90 mt-4">Event Details</h3>
                    <p className="text-sm text-white/70 mt-2 bg-black/20 p-3 rounded-lg border border-white/5">
                      {selectedEvent.reason}
                    </p>
                  </div>

                  <div className="space-y-4">
                    <h4 className="text-xs font-bold text-white/40 uppercase tracking-wider">System Provenance</h4>
                    
                    <div className="bg-black/30 rounded-xl p-4 border border-white/5 space-y-4">
                      
                      <div className="flex justify-between items-center border-b border-white/5 pb-3">
                        <div className="flex items-center gap-2 text-white/60">
                          <Code2 className="w-4 h-4" />
                          <span className="text-xs">Policy Version</span>
                        </div>
                        <span className="text-sm font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                          {selectedEvent.policy_version || "v1.0.0"}
                        </span>
                      </div>

                      <div className="flex justify-between items-center border-b border-white/5 pb-3">
                        <div className="flex items-center gap-2 text-white/60">
                          <Cpu className="w-4 h-4" />
                          <span className="text-xs">Model Checkpoint</span>
                        </div>
                        <span className="text-sm font-mono text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded">
                          {selectedEvent.model_version || "n/a"}
                        </span>
                      </div>

                      <div className="flex justify-between items-center border-b border-white/5 pb-3">
                        <div className="flex items-center gap-2 text-white/60">
                          <ShieldCheck className="w-4 h-4" />
                          <span className="text-xs">Deterministic Rule</span>
                        </div>
                        <span className="text-sm font-medium text-white/80">
                          {selectedEvent.decision || "None"}
                        </span>
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-white/60 flex items-center gap-1"><Zap className="w-3 h-3" /> Correlation ID</span>
                        </div>
                        <div className="bg-black/40 text-xs text-white/50 font-mono p-2 rounded break-all border border-white/5">
                          {selectedEvent.id}
                        </div>
                      </div>

                    </div>
                  </div>

                  {selectedEvent.case_id && (
                    <div className="pt-4">
                      <Link 
                        href={`/cases/${selectedEvent.case_id}`}
                        className="w-full flex items-center justify-center gap-2 bg-brand-500/10 hover:bg-brand-500/20 text-brand-300 border border-brand-500/30 px-4 py-2.5 rounded-xl transition-colors text-sm font-semibold"
                      >
                        View Full Case <ArrowRight className="w-4 h-4" />
                      </Link>
                    </div>
                  )}

                </motion.div>
              ) : (
                <div className="h-full flex flex-col items-center justify-center text-white/30 text-center min-h-[300px]">
                  <Search className="w-12 h-12 opacity-20 mb-4" />
                  <p className="text-sm">Select an event from the timeline<br/>to view its full execution trace.</p>
                </div>
              )}
            </AnimatePresence>
          </div>
        </div>

      </div>
    </div>
  );
}

function getTypeStyles(type: string) {
  if (type.includes("POLICY")) return { icon: Code2, bg: "bg-purple-500/10", color: "text-purple-400", border: "border-purple-500/30" };
  if (type.includes("RISK")) return { icon: AlertTriangle, bg: "bg-orange-500/10", color: "text-orange-400", border: "border-orange-500/30" };
  if (type.includes("ACTION")) return { icon: Zap, bg: "bg-blue-500/10", color: "text-blue-400", border: "border-blue-500/30" };
  if (type.includes("RECONCILIATION")) return { icon: RefreshCcw, bg: "bg-emerald-500/10", color: "text-emerald-400", border: "border-emerald-500/30" };
  if (type.includes("BLOCKED") || type.includes("FAILED")) return { icon: AlertTriangle, bg: "bg-rose-500/10", color: "text-rose-400", border: "border-rose-500/30" };
  return { icon: ShieldCheck, bg: "bg-white/5", color: "text-white/60", border: "border-white/20" };
}
