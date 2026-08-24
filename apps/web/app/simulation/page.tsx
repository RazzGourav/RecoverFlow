"use client";

import { SimulationClient } from "./SimulationClient";

export default function SimulationLabPage() {
  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full h-[calc(100vh-2rem)] flex flex-col">
      <header className="mb-8 shrink-0">
        <h1 className="text-3xl font-bold tracking-tight text-white/90">Counterfactual Simulation Lab</h1>
        <p className="text-white/50 text-sm mt-1 max-w-2xl">
          Run the full real pipeline—from ML prediction through risk firewall and policy engine—in dry-run mode. 
          Compare the RecoverFlow budget-optimized AI decisions against static rules on live OPEN cases.
        </p>
      </header>

      <div className="flex-1 min-h-0">
        <SimulationClient />
      </div>
    </div>
  );
}
