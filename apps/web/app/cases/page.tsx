import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

export const metadata: Metadata = {
  title: "Recovery Cases | RecoverFlow",
  description: "View and filter all revenue recovery cases.",
};

async function getCases(searchParams: any) {
  // INTERNAL_API_URL is set in docker-compose for server-to-server calls.
  // Falls back to api:8000 (Docker default) or localhost for local dev.
  const apiBase =
    process.env.INTERNAL_API_URL ??
    process.env.NEXT_PUBLIC_API_URL ??
    "http://api:8000";
  try {
    const params = new URLSearchParams(searchParams);
    const res = await fetch(`${apiBase}/cases?${params.toString()}`, { cache: "no-store" });
    if (!res.ok) return [];
    return res.json();
  } catch (e) {
    return [];
  }
}

import { CasesTable } from "./CasesTable";

export default async function CasesPage({ searchParams }: { searchParams: any }) {
  const cases = await getCases(searchParams);

  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full">
      <div className="relative z-10 space-y-8">
        
        {/* Header */}
        <header>
          <h1 className="text-3xl font-bold tracking-tight text-white/90">Recovery Cases</h1>
          <p className="text-white/50 text-sm mt-1">Review, filter, and manage all revenue recovery workflows.</p>
        </header>

        {/* Client-side Table */}
        <Suspense fallback={<div className="p-8 text-center text-white/50">Loading cases...</div>}>
          <CasesTable initialCases={cases} />
        </Suspense>

      </div>
    </div>
  );
}
