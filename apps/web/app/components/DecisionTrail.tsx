"use client";

import { useState } from "react";

export default function DecisionTrail({ caseData }: { caseData: any }) {
  const [isOpen, setIsOpen] = useState(false);

  // Extract relevant audit events for the trail
  const validationEvent = caseData.audit_events?.find((e: any) => 
    e.event_type === "VALIDATION_BLOCKED" || e.event_type === "ACTION_EXECUTED"
  );
  
  const optimizerEvent = caseData.audit_events?.find((e: any) => 
    e.event_type === "BUDGET_EXHAUSTED" || e.event_type === "ACTION_APPROVED"
  );

  const riskEvent = caseData.audit_events?.find((e: any) => 
    e.event_type === "RISK_FIREWALL_EVALUATED" || e.event_type === "RISK_FIREWALL_BLOCKED"
  );

  const hasLLM = !!caseData.llm_explanation;

  if (!hasLLM && !optimizerEvent && !validationEvent) return null;

  return (
    <div className="mt-6 border border-white/10 rounded-xl overflow-hidden bg-black/20">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors focus:outline-none"
      >
        <div className="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#06b6d4]"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          <span className="text-sm font-medium text-white/90">Explain This ₹{(caseData.amount_paise / 100).toLocaleString()}</span>
        </div>
        <svg 
          xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" 
          className={`text-white/40 transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {isOpen && (
        <div className="p-4 pt-0 border-t border-white/5 space-y-4">
          <div className="relative pl-4 border-l-2 border-white/10 space-y-4">
            
            {/* Funnel Source */}
            <div className="relative">
              <div className="absolute w-2 h-2 bg-purple-500 rounded-full -left-[21px] top-1.5" />
              <p className="text-xs font-semibold text-purple-400 mb-0.5">1. Funnel Ingestion</p>
              <p className="text-sm text-white/70">
                Customer dropped off at <span className="font-mono text-white/90">PAYMENT_ATTEMPTED</span> stage.
              </p>
            </div>

            {/* Risk & Policy */}
            {(riskEvent || hasLLM) && (
              <div className="relative">
                <div className="absolute w-2 h-2 bg-blue-500 rounded-full -left-[21px] top-1.5" />
                <p className="text-xs font-semibold text-blue-400 mb-0.5">2. Policy & Risk AI</p>
                <div className="text-sm text-white/70 italic border-l-2 border-blue-500/30 pl-2 ml-1 mt-1">
                  "{caseData.llm_explanation || (riskEvent ? riskEvent.reason : "Evaluated safely.")}"
                </div>
              </div>
            )}

            {/* Optimizer */}
            {optimizerEvent && (
              <div className="relative">
                <div className={`absolute w-2 h-2 rounded-full -left-[21px] top-1.5 ${optimizerEvent.event_type === 'BUDGET_EXHAUSTED' ? 'bg-red-500' : 'bg-green-500'}`} />
                <p className={`text-xs font-semibold mb-0.5 ${optimizerEvent.event_type === 'BUDGET_EXHAUSTED' ? 'text-red-400' : 'text-green-400'}`}>
                  3. Budget Optimizer
                </p>
                <p className="text-sm text-white/70">
                  {optimizerEvent.reason}
                </p>
              </div>
            )}

            {/* Validation Layer */}
            {validationEvent && (
              <div className="relative">
                <div className={`absolute w-2 h-2 rounded-full -left-[21px] top-1.5 ${validationEvent.event_type === 'VALIDATION_BLOCKED' ? 'bg-orange-500' : 'bg-[#06b6d4]'}`} />
                <p className={`text-xs font-semibold mb-0.5 ${validationEvent.event_type === 'VALIDATION_BLOCKED' ? 'text-orange-400' : 'text-[#06b6d4]'}`}>
                  4. Validation Layer
                </p>
                <p className="text-sm text-white/70">
                  {validationEvent.reason}
                </p>
              </div>
            )}
            
          </div>
        </div>
      )}
    </div>
  );
}
