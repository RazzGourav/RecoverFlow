"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function PolicyStudioPage() {
  const [policy, setPolicy] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/policies")
      .then(res => res.json())
      .then(data => {
        setPolicy(data);
        setLoading(false);
      })
      .catch(e => {
        console.error(e);
        setLoading(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!policy) return;
    setSaving(true);
    setMessage("");

    try {
      const res = await fetch(`http://localhost:8000/policies/${policy.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          max_autonomous_amount_paise: policy.max_autonomous_amount_paise,
          retry_limit: policy.retry_limit,
          cooldown_hours: policy.cooldown_hours,
          confidence_threshold: policy.confidence_threshold,
          human_review_threshold_paise: policy.human_review_threshold_paise
        })
      });

      if (res.ok) {
        setMessage("Policy updated successfully.");
      } else {
        setMessage("Failed to update policy.");
      }
    } catch (e) {
      setMessage("An error occurred.");
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setPolicy((prev: any) => ({ ...prev, [name]: parseFloat(value) }));
  };

  if (loading) {
    return <div className="min-h-screen bg-[#0b1326] flex items-center justify-center text-white/50">Loading policy data...</div>;
  }

  return (
    <div className="min-h-screen bg-[#0b1326] text-white p-8 font-sans selection:bg-brand-500/30">
      <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
        <div className="absolute top-1/4 left-1/4 w-[500px] h-[500px] bg-[#d946ef]/10 rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-3xl mx-auto space-y-8">
        <header className="flex items-center gap-4">
          <Link href="/" className="text-white/40 hover:text-white transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </Link>
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-white/90">Policy Studio</h1>
            <p className="text-white/50 text-sm mt-1">Configure global AI decision guardrails and financial limits.</p>
          </div>
        </header>

        {policy && (
          <form onSubmit={handleSubmit} className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-8 shadow-2xl space-y-6">
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">Max Autonomous Action Value (Paise)</label>
                <p className="text-xs text-white/40 mb-2">Maximum amount the AI is permitted to spend without human approval.</p>
                <input 
                  type="number" 
                  name="max_autonomous_amount_paise" 
                  value={policy.max_autonomous_amount_paise} 
                  onChange={handleChange}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#06b6d4] focus:ring-1 focus:ring-[#06b6d4] transition-all" 
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">Human Review Threshold (Paise)</label>
                <p className="text-xs text-white/40 mb-2">Cases above this amount will immediately be routed to humans.</p>
                <input 
                  type="number" 
                  name="human_review_threshold_paise" 
                  value={policy.human_review_threshold_paise} 
                  onChange={handleChange}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#06b6d4] focus:ring-1 focus:ring-[#06b6d4] transition-all" 
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">AI Confidence Threshold (0.0 - 1.0)</label>
                <p className="text-xs text-white/40 mb-2">Minimum ML probability required for the action optimizer to execute autonomously.</p>
                <input 
                  type="number" 
                  step="0.01" 
                  name="confidence_threshold" 
                  value={policy.confidence_threshold} 
                  onChange={handleChange}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#06b6d4] focus:ring-1 focus:ring-[#06b6d4] transition-all" 
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-1">Retry Limit</label>
                <p className="text-xs text-white/40 mb-2">Maximum number of automated interventions per case.</p>
                <input 
                  type="number" 
                  name="retry_limit" 
                  value={policy.retry_limit} 
                  onChange={handleChange}
                  className="w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-[#06b6d4] focus:ring-1 focus:ring-[#06b6d4] transition-all" 
                />
              </div>
            </div>

            <div className="pt-4 flex items-center justify-between border-t border-white/10">
              <span className="text-sm text-[#06b6d4]">{message}</span>
              <button 
                type="submit" 
                disabled={saving}
                className="bg-gradient-to-r from-[#06b6d4] to-blue-600 hover:from-[#06b6d4]/90 hover:to-blue-600/90 text-white font-medium px-6 py-2 rounded-lg transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Policy"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
