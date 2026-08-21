import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Audit Explorer | RecoverFlow",
  description: "Global audit trail across all recovery cases.",
};

async function getAuditLog(searchParams: any) {
  try {
    const params = new URLSearchParams(searchParams);
    const res = await fetch(`http://api:8000/audit?${params.toString()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

export default async function AuditExplorerPage({ searchParams }: { searchParams: any }) {
  const auditEvents = await getAuditLog(searchParams);

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#d946ef]/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-white/40 hover:text-white transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white/90">Audit Explorer</h1>
              <p className="text-white/50 text-sm mt-1">Immutable ledger of all autonomous decisions and actions.</p>
            </div>
          </div>
        </header>

        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          <FilterLink label="All Events" param="" currentParams={searchParams} />
          <FilterLink label="Policy Checks" param="event_type=POLICY_CHECK" currentParams={searchParams} />
          <FilterLink label="Risk Evaluations" param="event_type=RISK_EVALUATION" currentParams={searchParams} />
          <FilterLink label="Actions Executed" param="event_type=ACTION_EXECUTED" currentParams={searchParams} />
          <FilterLink label="Reconciliations" param="event_type=RECONCILIATION_MATCHED" currentParams={searchParams} />
        </div>

        {/* Table */}
        <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-white/5 text-white/40 border-b border-white/10 uppercase text-xs font-semibold tracking-wider">
                <tr>
                  <th className="px-6 py-4">Timestamp</th>
                  <th className="px-6 py-4">Event Type</th>
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Decision</th>
                  <th className="px-6 py-4">Reason / Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {auditEvents.map((ae: any) => (
                  <tr key={ae.id} className="hover:bg-white/5 transition-colors group">
                    <td className="px-6 py-4 text-white/60">{new Date(ae.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium border ${getTypeColor(ae.event_type)}`}>
                        {ae.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {ae.case_id ? (
                        <Link href={`/cases/${ae.case_id}`} className="text-[#06b6d4] font-medium group-hover:underline">
                          {ae.case_id.split("-")[0]}...
                        </Link>
                      ) : (
                        <span className="text-white/40">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className={ae.decision === 'ALLOW' ? 'text-[#06b6d4]' : ae.decision === 'BLOCK' ? 'text-red-400' : 'text-white/70'}>
                        {ae.decision || "—"}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-white/70 truncate max-w-md" title={ae.reason}>
                      {ae.reason}
                    </td>
                  </tr>
                ))}
                {auditEvents.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-6 py-12 text-center text-white/40">
                      No audit events found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

      </div>
    </div>
  );
}

function FilterLink({ label, param, currentParams }: { label: string, param: string, currentParams: any }) {
  const isActive = param === "" 
    ? Object.keys(currentParams).length === 0 
    : new URLSearchParams(currentParams).toString().includes(param);

  return (
    <Link 
      href={`/audit${param ? '?' + param : ''}`}
      className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
        isActive 
          ? "bg-[#06b6d4]/20 border-[#06b6d4]/40 text-white" 
          : "bg-white/5 border-white/10 text-white/60 hover:text-white/90 hover:bg-white/10"
      }`}
    >
      {label}
    </Link>
  );
}

function getTypeColor(type: string) {
  if (type.includes("POLICY")) return "bg-purple-500/10 text-purple-300 border-purple-500/30";
  if (type.includes("RISK")) return "bg-orange-500/10 text-orange-300 border-orange-500/30";
  if (type.includes("ACTION")) return "bg-blue-500/10 text-blue-300 border-blue-500/30";
  if (type.includes("RECONCILIATION")) return "bg-green-500/10 text-green-300 border-green-500/30";
  return "bg-white/5 text-white/60 border-white/10";
}
