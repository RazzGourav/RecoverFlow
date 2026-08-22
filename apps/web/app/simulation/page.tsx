"use client";

import { useState } from "react";
import Link from "next/link";

type StrategyResult = {
  strategy: string;
  expected_recovery_paise: number;
  cost_paise: number;
  net_recovery_paise: number;
  cases_processed: number;
  vs_optimal_paise: number;
};

export default function SimulationLabPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<StrategyResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      // Simulate across a sample of 100 cases with 5000 INR budget (500000 paise)
      const res = await fetch("http://localhost:8000/simulate/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ sample_size: 100, budget_paise: 500000 }),
      });
      if (!res.ok) {
        throw new Error(`Failed with status ${res.status}`);
      }
      const data = await res.json();
      
      // Sort so RECOVERFLOW_OPTIMAL is at top, then by net recovery descending
      const sorted = data.results.sort((a: StrategyResult, b: StrategyResult) => {
        if (a.strategy === "RECOVERFLOW_OPTIMAL") return -1;
        if (b.strategy === "RECOVERFLOW_OPTIMAL") return 1;
        return b.net_recovery_paise - a.net_recovery_paise;
      });
      
      setResults(sorted);
    } catch (err: any) {
      setError(err.message || "An error occurred during simulation.");
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (paise: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(paise / 100);
  };

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans">
      <div className="max-w-6xl mx-auto space-y-8 relative z-10">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-brand-300 text-sm mb-2">
              <Link href="/" className="hover:text-brand-100 transition-colors">Dashboard</Link>
              <span>/</span>
              <span>Simulation Lab</span>
            </div>
            <h1 className="text-3xl font-bold tracking-tight text-white/90">Counterfactual Recovery Simulator</h1>
            <p className="text-white/50 text-sm mt-1 max-w-2xl">
              Run the full real pipeline—from ML prediction through risk firewall and policy engine—in dry-run mode. Compare the RecoverFlow budget-optimized AI decisions against static rules on live OPEN cases.
            </p>
          </div>
          
          <button 
            onClick={runSimulation}
            disabled={loading}
            className="px-6 py-3 bg-[#d946ef]/20 hover:bg-[#d946ef]/40 text-[#f0abfc] border border-[#d946ef]/40 rounded-lg font-semibold shadow-[0_0_15px_rgba(217,70,239,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Running Simulation..." : "▶ Run Strategy Comparison"}
          </button>
        </header>

        {error && (
          <div className="p-4 bg-red-900/40 border border-red-500/50 rounded-lg text-red-200">
            <strong>Simulation Failed: </strong> {error}
          </div>
        )}

        {results && (
          <section className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h2 className="text-xl font-semibold mb-4 text-white/80">Comparison Results (n = {results[0]?.cases_processed} cases)</h2>
            <div className="overflow-hidden rounded-xl border border-white/10 bg-[#1e1b4b]/40 backdrop-blur-xl shadow-2xl">
              <table className="w-full text-left text-sm">
                <thead className="bg-white/5 border-b border-white/10">
                  <tr>
                    <th className="p-4 font-medium text-white/60">Strategy</th>
                    <th className="p-4 font-medium text-white/60 text-right">Expected Recovery</th>
                    <th className="p-4 font-medium text-white/60 text-right">Action Cost</th>
                    <th className="p-4 font-medium text-white/60 text-right">Net Recovery</th>
                    <th className="p-4 font-medium text-white/60 text-right">vs Optimal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {results.map((r, i) => {
                    const isOptimal = r.strategy === "RECOVERFLOW_OPTIMAL";
                    return (
                      <tr 
                        key={r.strategy} 
                        className={`transition-colors ${isOptimal ? "bg-[#06b6d4]/10 hover:bg-[#06b6d4]/20" : "hover:bg-white/5"}`}
                      >
                        <td className="p-4">
                          <div className="flex items-center gap-3">
                            <span className={`font-mono ${isOptimal ? "text-[#06b6d4] font-bold" : "text-white/80"}`}>
                              {r.strategy}
                            </span>
                            {isOptimal && (
                              <span className="px-2 py-0.5 rounded text-xs bg-[#06b6d4]/20 text-[#06b6d4] border border-[#06b6d4]/30">
                                Recommended
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="p-4 text-right font-medium text-green-400">
                          {formatCurrency(r.expected_recovery_paise)}
                        </td>
                        <td className="p-4 text-right font-medium text-red-400">
                          {formatCurrency(r.cost_paise)}
                        </td>
                        <td className={`p-4 text-right font-bold ${isOptimal ? "text-white" : "text-white/80"}`}>
                          {formatCurrency(r.net_recovery_paise)}
                        </td>
                        <td className="p-4 text-right">
                          {isOptimal ? (
                            <span className="text-white/40">—</span>
                          ) : (
                            <span className={r.vs_optimal_paise < 0 ? "text-red-400" : "text-green-400"}>
                              {r.vs_optimal_paise < 0 ? "" : "+"}{formatCurrency(r.vs_optimal_paise)}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </section>
        )}
        
        {/* Placeholder before simulation runs */}
        {!results && !loading && !error && (
          <div className="flex flex-col items-center justify-center p-12 text-center bg-[#1e1b4b]/20 border border-white/5 rounded-2xl backdrop-blur-md h-64">
            <div className="w-16 h-16 rounded-full bg-[#d946ef]/10 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-[#d946ef]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-white/80">Simulator Ready</h3>
            <p className="text-white/50 text-sm mt-2 max-w-md">
              Click the button above to pit RecoverFlow's budget-aware AI directly against static legacy rules across a live batch of failed payments.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
