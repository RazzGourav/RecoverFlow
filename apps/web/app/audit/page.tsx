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

import { AuditClient } from "./AuditClient";

export default async function AuditExplorerPage({ searchParams }: { searchParams: any }) {
  const auditEvents = await getAuditLog(searchParams);

  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full h-screen overflow-hidden flex flex-col">
      
      <header className="mb-8 shrink-0">
        <h1 className="text-3xl font-bold tracking-tight text-white/90">Audit Explorer</h1>
        <p className="text-white/50 text-sm mt-1">Immutable ledger of all autonomous decisions and actions.</p>
      </header>

      <AuditClient initialEvents={auditEvents} />

    </div>
  );
}
