import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Recovery Cases | RecoverFlow",
  description: "View and filter all revenue recovery cases.",
};

async function getCases(searchParams: any) {
  try {
    const params = new URLSearchParams(searchParams);
    const res = await fetch(`http://api:8000/cases?${params.toString()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

export default async function CasesPage({ searchParams }: { searchParams: any }) {
  const cases = await getCases(searchParams);

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      {/* Background glow effects for glassmorphism */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#06b6d4]/10 rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 left-1/4 w-[600px] h-[600px] bg-[#d946ef]/10 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="text-white/40 hover:text-white transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </Link>
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-white/90">Recovery Cases</h1>
              <p className="text-white/50 text-sm mt-1">Review and manage all revenue recovery workflows.</p>
            </div>
          </div>
        </header>

        {/* Filters */}
        <div className="flex flex-wrap gap-4">
          <FilterLink label="All Cases" param="" currentParams={searchParams} />
          <FilterLink label="High Risk" param="risk_level=HIGH" currentParams={searchParams} />
          <FilterLink label="Pending" param="status=PENDING" currentParams={searchParams} />
          <FilterLink label="Recovered" param="status=RECOVERED" currentParams={searchParams} />
        </div>

        {/* Table */}
        <section className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 overflow-hidden shadow-2xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-white/5 text-white/40 border-b border-white/10 uppercase text-xs font-semibold tracking-wider">
                <tr>
                  <th className="px-6 py-4">Case ID</th>
                  <th className="px-6 py-4">Created At</th>
                  <th className="px-6 py-4">Amount</th>
                  <th className="px-6 py-4">Customer Segment</th>
                  <th className="px-6 py-4">Failure Type</th>
                  <th className="px-6 py-4">Risk Level</th>
                  <th className="px-6 py-4 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {cases.map((c: any) => (
                  <tr key={c.id} className="hover:bg-white/5 transition-colors group">
                    <td className="px-6 py-4">
                      <Link href={`/cases/${c.id}`} className="text-[#06b6d4] font-medium group-hover:underline">
                        {c.id.split("-")[0]}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-white/60">{new Date(c.created_at).toLocaleString()}</td>
                    <td className="px-6 py-4 font-semibold">₹{(c.amount_paise / 100).toLocaleString()}</td>
                    <td className="px-6 py-4 text-white/70">{c.customer_segment || "UNKNOWN"}</td>
                    <td className="px-6 py-4 text-white/70">{c.failure_type}</td>
                    <td className="px-6 py-4">
                      {c.risk_level === "HIGH" ? (
                        <span className="text-[#d946ef] font-semibold">{c.risk_level}</span>
                      ) : (
                        <span className="text-white/40">{c.risk_level || "—"}</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(c.status)}`}>
                        {c.status}
                      </span>
                    </td>
                  </tr>
                ))}
                {cases.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-white/40">
                      No cases found matching the criteria.
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
      href={`/cases${param ? '?' + param : ''}`}
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

function getStatusColor(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-[#06b6d4]/10 text-[#06b6d4] border-[#06b6d4]/30';
    case 'PENDING': return 'bg-yellow-500/10 text-yellow-300 border-yellow-500/30';
    case 'FAILED': return 'bg-red-500/10 text-red-400 border-red-500/30';
    default: return 'bg-white/5 text-white/60 border-white/10';
  }
}
