import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

export const metadata: Metadata = {
  title: "Case Intelligence | RecoverFlow",
  description: "Deep view of a revenue recovery case.",
};

async function getCase(id: string) {
  try {
    const res = await fetch(`http://api:8000/cases/${id}`, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error("Failed to fetch case");
    return res.json();
  } catch (e) {
    return null;
  }
}

export default async function CaseIntelligencePage({ params }: { params: { id: string } }) {
  const caseData = await getCase(params.id);

  if (!caseData) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      {/* Background glow effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#06b6d4]/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-5xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Link href="/cases" className="text-white/40 hover:text-white transition-colors">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
              </Link>
              <h1 className="text-2xl font-bold tracking-tight text-white/90 font-mono">Case {caseData.id.split("-")[0]}</h1>
            </div>
            <div className="flex flex-wrap items-center gap-3 ml-8">
              <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(caseData.status)}`}>
                {caseData.status}
              </span>
              <span className="text-white/40 text-sm">Created {new Date(caseData.created_at).toLocaleString()}</span>
            </div>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-[#06b6d4]">₹{(caseData.amount_paise / 100).toLocaleString()}</div>
            <div className="text-white/50 text-sm uppercase tracking-wider">{caseData.failure_type}</div>
          </div>
        </header>

        {/* Intelligence Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          
          {/* Customer & Risk Context */}
          <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6">
            <h2 className="text-lg font-semibold text-white/80 mb-4 border-b border-white/10 pb-2">Customer & Risk Profile</h2>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-white/40 mb-1">Segment</p>
                <p className="text-sm font-medium">{caseData.customer?.segment || "Unknown"}</p>
              </div>
              <div>
                <p className="text-xs text-white/40 mb-1">Tenure</p>
                <p className="text-sm font-medium">{caseData.customer?.tenure_days || 0} days</p>
              </div>
              <div>
                <p className="text-xs text-white/40 mb-1">Recoverability Score</p>
                <p className="text-sm font-medium text-[#06b6d4]">
                  {caseData.recoverability_score ? `${(caseData.recoverability_score * 100).toFixed(1)}%` : "Pending"}
                </p>
              </div>
              <div>
                <p className="text-xs text-white/40 mb-1">Risk Level</p>
                <p className={`text-sm font-medium ${caseData.risk_level === 'HIGH' ? 'text-[#d946ef]' : ''}`}>
                  {caseData.risk_level || "Unknown"}
                </p>
              </div>
            </div>
            
            {caseData.llm_explanation && (
              <div className="mt-6 bg-black/20 rounded-lg p-4 text-sm text-white/70 italic border-l-2 border-[#06b6d4]">
                "{caseData.llm_explanation}"
              </div>
            )}
          </section>

          {/* Action Decision */}
          <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6 flex flex-col">
            <h2 className="text-lg font-semibold text-white/80 mb-4 border-b border-white/10 pb-2">Action Optimizer</h2>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="text-white/40 text-xs">
                    <th className="pb-2 font-normal">Candidate Action</th>
                    <th className="pb-2 font-normal text-right">Probability</th>
                    <th className="pb-2 font-normal text-right">Expected Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {caseData.candidate_actions.map((ca: any, i: number) => (
                    <tr key={ca.id} className={i === 0 ? "text-[#06b6d4]" : "text-white/60"}>
                      <td className="py-2">{ca.action_type} {i === 0 && <span className="ml-2 text-xs bg-[#06b6d4]/20 text-[#06b6d4] px-2 py-0.5 rounded">Selected</span>}</td>
                      <td className="py-2 text-right">{(ca.probability * 100).toFixed(1)}%</td>
                      <td className="py-2 text-right">₹{(ca.expected_value_paise / 100).toLocaleString()}</td>
                    </tr>
                  ))}
                  {caseData.candidate_actions.length === 0 && (
                    <tr><td colSpan={3} className="py-4 text-center text-white/40">No actions evaluated</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

        </div>

        {/* Audit Trail */}
        <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-6">
          <h2 className="text-lg font-semibold text-white/80 mb-6 border-b border-white/10 pb-2">Audit Trail</h2>
          <div className="space-y-6">
            {caseData.audit_events.map((ae: any) => (
              <div key={ae.id} className="relative pl-6 border-l border-white/10">
                <div className="absolute w-2 h-2 bg-[#06b6d4] rounded-full -left-[4.5px] top-1.5 shadow-[0_0_8px_#06b6d4]" />
                <div className="flex flex-col sm:flex-row sm:items-baseline justify-between mb-1">
                  <h3 className="text-sm font-semibold text-white">{ae.event_type}</h3>
                  <span className="text-xs text-white/40">{new Date(ae.timestamp).toLocaleString()}</span>
                </div>
                <div className="text-sm">
                  {ae.decision && <span className="font-medium text-[#d946ef] mr-2">[{ae.decision}]</span>}
                  <span className="text-white/70">{ae.reason}</span>
                </div>
              </div>
            ))}
            {caseData.audit_events.length === 0 && (
              <div className="text-white/40 text-sm italic">No audit events recorded for this case.</div>
            )}
          </div>
        </section>

      </div>
    </div>
  );
}

function getStatusColor(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-[#06b6d4]/10 text-[#06b6d4] border-[#06b6d4]/30';
    case 'PENDING': return 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30';
    case 'FAILED': return 'bg-red-500/10 text-red-400 border-red-500/30';
    default: return 'bg-white/5 text-white/60 border-white/10';
  }
}
