"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Settings2, ShieldCheck, User, Zap, AlertTriangle, Save, RefreshCcw } from "lucide-react";
import { cn } from "../components/utils";

export default function PolicyStudioPage() {
  const [policy, setPolicy] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("/api/policies/")
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
      const res = await fetch(`/api/policies/${policy.id}`, {
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
        setMessage("Policy saved successfully.");
        setTimeout(() => setMessage(""), 3000);
      } else {
        setMessage("Failed to save policy.");
      }
    } catch (e) {
      setMessage("An error occurred.");
    } finally {
      setSaving(false);
    }
  };

  const handleChange = (name: string, value: number) => {
    setPolicy((prev: any) => ({ ...prev, [name]: value }));
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center min-h-[60vh]">
        <RefreshCcw className="w-8 h-8 animate-spin text-brand-500" />
      </div>
    );
  }

  // Live Consequence Computation
  const sampleCases = [
    { id: "CASE-120", amount: 250000, confidence: 0.82, risk: "LOW" }, // ₹2,500
    { id: "CASE-121", amount: 1500000, confidence: 0.95, risk: "LOW" }, // ₹15,000
    { id: "CASE-122", amount: 50000, confidence: 0.65, risk: "HIGH" }, // ₹500
  ];

  const getRouting = (c: any) => {
    if (c.amount >= policy.human_review_threshold_paise) {
      return { status: "HUMAN_REVIEW", reason: "Exceeds absolute human review threshold", icon: User, color: "text-orange-400", bg: "bg-orange-500/10" };
    }
    if (c.amount > policy.max_autonomous_amount_paise) {
      return { status: "HUMAN_REVIEW", reason: "Exceeds autonomous execution limit", icon: User, color: "text-orange-400", bg: "bg-orange-500/10" };
    }
    if (c.confidence < policy.confidence_threshold) {
      return { status: "HUMAN_REVIEW", reason: "ML confidence below threshold", icon: AlertTriangle, color: "text-yellow-400", bg: "bg-yellow-500/10" };
    }
    return { status: "AUTONOMOUS", reason: "Within safe autonomous limits", icon: Zap, color: "text-[#06b6d4]", bg: "bg-[#06b6d4]/10" };
  };

  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full">
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-white/90">Policy Studio</h1>
        <p className="text-white/50 text-sm mt-1">Configure global AI decision guardrails and financial limits.</p>
      </header>

      {policy && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          
          {/* Controls Form */}
          <motion.form 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            onSubmit={handleSubmit} 
            className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/10 p-8 shadow-2xl flex flex-col h-full"
          >
            <div className="flex items-center gap-3 mb-8 pb-4 border-b border-white/10">
              <Settings2 className="w-5 h-5 text-brand-400" />
              <h2 className="text-lg font-semibold text-white/80">Guardrail Parameters</h2>
            </div>

            <div className="space-y-8 flex-1">
              
              <SliderControl 
                label="Max Autonomous Spend"
                description="Maximum amount the AI can spend or discount without human approval."
                value={policy.max_autonomous_amount_paise}
                min={0}
                max={500000} // 5k INR
                step={10000}
                onChange={(v: number) => handleChange("max_autonomous_amount_paise", v)}
                formatter={(v: number) => `₹${(v / 100).toLocaleString()}`}
              />

              <SliderControl 
                label="Human Review Threshold"
                description="Hard limit above which all cases require human review."
                value={policy.human_review_threshold_paise}
                min={0}
                max={2000000} // 20k INR
                step={50000}
                onChange={(v: number) => handleChange("human_review_threshold_paise", v)}
                formatter={(v: number) => `₹${(v / 100).toLocaleString()}`}
              />

              <SliderControl 
                label="AI Confidence Threshold"
                description="Minimum ML probability required for the action optimizer to execute."
                value={policy.confidence_threshold}
                min={0.5}
                max={0.99}
                step={0.01}
                onChange={(v: number) => handleChange("confidence_threshold", v)}
                formatter={(v: number) => `${(v * 100).toFixed(0)}%`}
              />

              <SliderControl 
                label="Retry Intervention Limit"
                description="Maximum number of automated interventions per case."
                value={policy.retry_limit}
                min={1}
                max={5}
                step={1}
                onChange={(v: number) => handleChange("retry_limit", v)}
                formatter={(v: number) => `${v} interventions`}
              />

            </div>

            <div className="pt-6 mt-8 flex items-center justify-between border-t border-white/10">
              <span className="text-sm font-medium text-emerald-400">{message}</span>
              <button 
                type="submit" 
                disabled={saving}
                className="flex items-center gap-2 bg-gradient-to-r from-brand-500 to-[#d946ef] hover:from-brand-500/90 hover:to-[#d946ef]/90 text-white font-bold px-6 py-2.5 rounded-xl transition-all shadow-[0_0_15px_rgba(217,70,239,0.3)] disabled:opacity-50"
              >
                {saving ? <RefreshCcw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                {saving ? "Deploying..." : "Deploy Policy"}
              </button>
            </div>
          </motion.form>

          {/* Live Consequence Viewer */}
          <motion.div 
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-brand-500/20 p-8 shadow-2xl relative overflow-hidden"
          >
            <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-brand-500/10 rounded-full blur-[100px] pointer-events-none" />
            
            <div className="flex items-center gap-3 mb-8 pb-4 border-b border-brand-500/20 relative z-10">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-white/90">Live Consequence Viewer</h2>
            </div>

            <p className="text-sm text-white/50 mb-6 relative z-10">
              Watch how your policy adjustments instantly re-route these sample cases in production.
            </p>

            <div className="space-y-4 relative z-10">
              <AnimatePresence mode="popLayout">
                {sampleCases.map(c => {
                  const route = getRouting(c);
                  return (
                    <motion.div 
                      key={c.id}
                      layout
                      className={cn("p-5 rounded-xl border transition-all duration-300", route.bg, route.color.replace('text-', 'border-').replace('400', '500/30'))}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <h4 className="font-bold text-white tracking-tight">{c.id}</h4>
                          <div className="flex gap-3 text-xs mt-1 text-white/60 font-medium">
                            <span>Value: ₹{(c.amount / 100).toLocaleString()}</span>
                            <span>Risk: {c.risk}</span>
                            <span>Conf: {(c.confidence * 100).toFixed(0)}%</span>
                          </div>
                        </div>
                        <div className={cn("px-3 py-1 rounded-full text-xs font-bold flex items-center gap-1.5 border border-white/10", route.bg, route.color)}>
                          <route.icon className="w-3.5 h-3.5" />
                          {route.status}
                        </div>
                      </div>
                      <div className="text-sm font-medium text-white/80 flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-current opacity-50" />
                        {route.reason}
                      </div>
                    </motion.div>
                  )
                })}
              </AnimatePresence>
            </div>
          </motion.div>

        </div>
      )}
    </div>
  );
}

function SliderControl({ label, description, value, min, max, step, onChange, formatter }: any) {
  // Calculate percentage for custom track styling
  const percentage = ((value - min) / (max - min)) * 100;
  
  return (
    <div>
      <div className="flex justify-between items-end mb-2">
        <div>
          <label className="block text-sm font-semibold text-white/90">{label}</label>
          <p className="text-xs text-white/40 mt-0.5">{description}</p>
        </div>
        <div className="text-lg font-bold text-brand-300 font-mono bg-brand-500/10 px-3 py-1 rounded-lg border border-brand-500/20">
          {formatter(value)}
        </div>
      </div>
      <input 
        type="range" 
        min={min} 
        max={max} 
        step={step}
        value={value} 
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer mt-2"
        style={{
          background: `linear-gradient(to right, #06b6d4 ${percentage}%, rgba(255,255,255,0.1) ${percentage}%)`
        }}
      />
      <style jsx>{`
        input[type=range]::-webkit-slider-thumb {
          appearance: none;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #fff;
          border: 2px solid #06b6d4;
          cursor: pointer;
          box-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
        }
      `}</style>
    </div>
  );
}
