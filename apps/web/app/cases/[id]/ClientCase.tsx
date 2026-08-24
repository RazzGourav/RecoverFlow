"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowLeft, Play, ShieldAlert, Sparkles, Target, Activity, CheckCircle2, CircleDollarSign, AlertCircle, RefreshCcw, Lock } from "lucide-react";
import { cn } from "../../components/utils";

export function ClientCase({ caseData }: { caseData: any }) {
  const hasLLM = !!caseData.llm_explanation;
  
  // Find specific events for the pipeline visualization
  const validationEvent = caseData.audit_events?.find((e: any) => e.event_type === "VALIDATION_BLOCKED" || e.event_type === "ACTION_EXECUTED");
  const optimizerEvent = caseData.audit_events?.find((e: any) => e.event_type === "BUDGET_EXHAUSTED" || e.event_type === "ACTION_APPROVED");
  const riskEvent = caseData.audit_events?.find((e: any) => e.event_type === "RISK_FIREWALL_EVALUATED" || e.event_type === "RISK_FIREWALL_BLOCKED");
  const reconciliationEvent = caseData.audit_events?.find((e: any) => e.event_type === "RECONCILIATION_EXCEPTION"); // usually reconciliation is a separate record, but we'll check if it failed

  const pipelineSteps = [
    {
      id: "context",
      title: "Customer & Payment Context",
      icon: UserIcon,
      color: "text-blue-400",
      bgGlow: "bg-blue-500/10",
      borderColor: "border-blue-500/20",
      content: (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-3">
          <DetailBox label="Segment" value={caseData.customer?.segment || "Unknown"} />
          <DetailBox label="Tenure" value={`${caseData.customer?.tenure_days || 0} days`} />
          <DetailBox label="Failure Type" value={caseData.failure_type} />
          <DetailBox label="Amount" value={`₹${(caseData.amount_paise / 100).toLocaleString()}`} />
        </div>
      )
    },
    {
      id: "ml",
      title: "ML Prediction Engine",
      icon: Sparkles,
      color: "text-brand-400",
      bgGlow: "bg-brand-500/10",
      borderColor: "border-brand-500/20",
      content: (
        <div className="mt-3">
          <div className="flex items-center gap-4 mb-4">
            <div className="flex-1 bg-black/20 rounded-lg p-3 border border-white/5">
              <span className="text-xs text-white/50 block mb-1">Recoverability Score</span>
              <span className="text-xl font-bold text-brand-400">
                {caseData.recoverability_score ? `${(caseData.recoverability_score * 100).toFixed(1)}%` : "Pending"}
              </span>
            </div>
            <div className="flex-1 bg-black/20 rounded-lg p-3 border border-white/5">
              <span className="text-xs text-white/50 block mb-1">Top Candidate</span>
              <span className="text-lg font-bold text-white/90">
                {caseData.candidate_actions?.[0]?.action_type || "None"}
              </span>
            </div>
          </div>
          {caseData.candidate_actions?.length > 0 && (
            <div className="text-xs text-white/40">
              Evaluated {caseData.candidate_actions.length} candidate actions based on expected value.
            </div>
          )}
        </div>
      )
    },
    {
      id: "risk",
      title: "Risk Firewall",
      icon: ShieldAlert,
      color: caseData.risk_level === "HIGH" ? "text-rose-400" : "text-emerald-400",
      bgGlow: caseData.risk_level === "HIGH" ? "bg-rose-500/10" : "bg-emerald-500/10",
      borderColor: caseData.risk_level === "HIGH" ? "border-rose-500/20" : "border-emerald-500/20",
      content: (
        <div className="mt-3">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-white/70">Risk Level:</span>
            <span className={cn("px-2 py-0.5 rounded text-xs font-bold", caseData.risk_level === "HIGH" ? "bg-rose-500/20 text-rose-400" : "bg-emerald-500/20 text-emerald-400")}>
              {caseData.risk_level || "UNKNOWN"}
            </span>
          </div>
          {riskEvent && (
            <div className="text-sm text-white/60 bg-black/20 p-3 rounded-lg border border-white/5">
              {riskEvent.reason}
            </div>
          )}
        </div>
      )
    },
    {
      id: "policy",
      title: "Decision Engine & LLM Reasoner",
      icon: Target,
      color: "text-[#d946ef]",
      bgGlow: "bg-[#d946ef]/10",
      borderColor: "border-[#d946ef]/20",
      content: (
        <div className="mt-3 space-y-3">
          {hasLLM ? (
            <div className="bg-[#d946ef]/5 border-l-2 border-[#d946ef] p-4 rounded-r-xl">
              <div className="flex items-center gap-2 mb-2">
                <Sparkles className="w-4 h-4 text-[#d946ef]" />
                <span className="text-xs font-bold text-[#d946ef] uppercase tracking-wider">AI Explanation</span>
              </div>
              <p className="text-sm text-white/80 italic leading-relaxed">
                "{caseData.llm_explanation}"
              </p>
            </div>
          ) : (
            <div className="text-sm text-white/50 italic p-3 bg-white/5 rounded-lg">
              Deterministic rule applied. No LLM override required.
            </div>
          )}
        </div>
      )
    },
    {
      id: "optimizer",
      title: "Budget Optimizer",
      icon: CircleDollarSign,
      color: optimizerEvent?.event_type === "BUDGET_EXHAUSTED" ? "text-rose-400" : "text-emerald-400",
      bgGlow: optimizerEvent?.event_type === "BUDGET_EXHAUSTED" ? "bg-rose-500/10" : "bg-emerald-500/10",
      borderColor: optimizerEvent?.event_type === "BUDGET_EXHAUSTED" ? "border-rose-500/20" : "border-emerald-500/20",
      content: optimizerEvent ? (
        <div className="mt-3 text-sm text-white/70 bg-black/20 p-3 rounded-lg border border-white/5">
          {optimizerEvent.reason}
        </div>
      ) : (
        <div className="mt-3 text-sm text-white/40 italic">Bypassed or Pending</div>
      )
    },
    {
      id: "validation",
      title: "Validation Layer (Pre-Execution)",
      icon: Lock,
      color: validationEvent?.event_type === "VALIDATION_BLOCKED" ? "text-orange-400" : "text-[#06b6d4]",
      bgGlow: validationEvent?.event_type === "VALIDATION_BLOCKED" ? "bg-orange-500/10" : "bg-[#06b6d4]/10",
      borderColor: validationEvent?.event_type === "VALIDATION_BLOCKED" ? "border-orange-500/20" : "border-[#06b6d4]/20",
      content: validationEvent ? (
        <div className="mt-3 text-sm text-white/70 bg-black/20 p-3 rounded-lg border border-white/5">
          {validationEvent.reason}
        </div>
      ) : (
        <div className="mt-3 text-sm text-white/40 italic">Pending Execution</div>
      )
    },
    {
      id: "status",
      title: "Execution & Reconciliation",
      icon: Activity,
      color: getStatusColorHex(caseData.status).text,
      bgGlow: getStatusColorHex(caseData.status).bg,
      borderColor: getStatusColorHex(caseData.status).border,
      content: (
        <div className="mt-3 flex items-center justify-between bg-black/20 p-4 rounded-xl border border-white/5">
          <div>
            <p className="text-xs text-white/50 mb-1">Final Status</p>
            <span className={cn("px-3 py-1 rounded-full text-xs font-bold border", getStatusColorClass(caseData.status))}>
              {caseData.status}
            </span>
          </div>
          {reconciliationEvent && (
            <div className="text-right">
              <p className="text-xs text-rose-400 mb-1">Reconciliation Exception</p>
              <p className="text-xs text-white/50 w-48 truncate">{reconciliationEvent.reason}</p>
            </div>
          )}
        </div>
      )
    }
  ];

  return (
    <div className="p-8 max-w-[1200px] mx-auto w-full pb-24">
      {/* Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-12">
        <div className="flex items-center gap-4">
          <Link href="/cases" className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center hover:bg-white/10 transition-colors border border-white/10">
            <ArrowLeft className="w-5 h-5 text-white/60" />
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white/90 font-mono">
              {caseData.id.split("-")[0]}
            </h1>
            <p className="text-white/50 text-sm mt-1">Created {new Date(caseData.created_at).toLocaleString()}</p>
          </div>
        </div>
        
        <div className="flex items-center gap-4">
          <div className="text-right mr-4">
            <div className="text-3xl font-bold text-white">₹{(caseData.amount_paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}</div>
            <div className="text-white/40 text-xs font-medium uppercase tracking-wider">{caseData.failure_type}</div>
          </div>
          <Link 
            href={`/cases/${caseData.id}/replay`}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-bold bg-[#06b6d4]/10 text-[#06b6d4] hover:bg-[#06b6d4]/20 border border-[#06b6d4]/30 transition-all shadow-[0_0_15px_rgba(6,182,212,0.15)] hover:shadow-[0_0_25px_rgba(6,182,212,0.3)]"
          >
            <Play className="w-4 h-4" />
            Replay Lab
          </Link>
        </div>
      </header>

      {/* Vertical Pipeline */}
      <div className="relative">
        {/* Connecting Line */}
        <div className="absolute left-8 top-10 bottom-10 w-0.5 bg-gradient-to-b from-blue-500/20 via-brand-500/20 to-emerald-500/20" />

        <div className="space-y-8">
          {pipelineSteps.map((step, idx) => (
            <motion.div 
              key={step.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.1 }}
              className="relative pl-24"
            >
              {/* Step Node Icon */}
              <div className={cn("absolute left-4 w-9 h-9 rounded-full flex items-center justify-center border-2 bg-[#0b1326] z-10", step.borderColor, step.color)}>
                <step.icon className="w-4 h-4" />
                {/* Glow behind icon */}
                <div className={cn("absolute inset-0 rounded-full blur-[10px] -z-10", step.bgGlow)} />
              </div>

              {/* Content Card */}
              <div className={cn("bg-[#1e1b4b]/40 backdrop-blur-xl rounded-2xl border p-5 shadow-2xl transition-colors hover:border-white/20", step.borderColor)}>
                <h3 className={cn("text-sm font-bold uppercase tracking-wider mb-2", step.color)}>
                  {idx + 1}. {step.title}
                </h3>
                {step.content}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DetailBox({ label, value }: { label: string, value: string | number }) {
  return (
    <div className="bg-black/20 p-3 rounded-lg border border-white/5">
      <p className="text-xs text-white/40 mb-1">{label}</p>
      <p className="text-sm font-semibold text-white/90">{value}</p>
    </div>
  );
}

function UserIcon(props: any) {
  return <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
}

function getStatusColorClass(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    case 'PENDING': 
    case 'EXECUTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    case 'HUMAN_REVIEW': return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
    case 'FAILED': 
    case 'UNRECOVERABLE':
    case 'BLOCKED': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    default: return 'bg-white/5 text-white/60 border-white/10';
  }
}

function getStatusColorHex(status: string) {
  switch (status) {
    case 'RECOVERED': return { text: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20' };
    case 'FAILED':
    case 'UNRECOVERABLE':
    case 'BLOCKED': return { text: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/20' };
    default: return { text: 'text-white/60', bg: 'bg-white/10', border: 'border-white/20' };
  }
}
