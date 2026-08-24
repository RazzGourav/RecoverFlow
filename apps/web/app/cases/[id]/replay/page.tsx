"use client";

import { ReplayClient } from "./ReplayClient";
import Link from "next/link";

export default function ReplayLabPage({ params }: { params: { id: string } }) {
  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full h-[calc(100vh-2rem)] flex flex-col">
      <header className="mb-8 shrink-0">
        <div className="flex items-center gap-3 mb-2">
          <Link href={`/cases/${params.id}`} className="text-white/40 hover:text-white transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </Link>
          <h1 className="text-3xl font-bold tracking-tight text-white/90">Event Replay Lab</h1>
        </div>
        <p className="text-white/50 text-sm ml-8">Simulate counterfactual strategies for Case {params.id.split("-")[0]}</p>
      </header>

      <div className="flex-1 min-h-0">
        <ReplayClient caseId={params.id} />
      </div>
    </div>
  );
}
