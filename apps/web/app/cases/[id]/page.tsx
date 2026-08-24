import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import DecisionTrail from "../../components/DecisionTrail";

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
  } catch (error) {
    return null;
  }
}

import { ClientCase } from "./ClientCase";

export default async function CaseIntelligencePage({ params }: { params: { id: string } }) {
  const caseData = await getCase(params.id);

  if (!caseData) {
    notFound();
  }

  return (
    <div className="min-h-screen bg-[#0b1326] text-white font-sans selection:bg-brand-500/30">
      {/* Background glow effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-0 right-1/4 w-[500px] h-[500px] bg-[#06b6d4]/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 w-full">
        <ClientCase caseData={caseData} />
      </div>
    </div>
  );
}
