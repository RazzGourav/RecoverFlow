import type { Metadata } from "next";

/**
 * RecoverFlow landing page (Phase 0 — stack validation placeholder).
 *
 * Why: Every phase must leave the system in a demoable state.  In Phase 0,
 * "demoable" means a visually compelling page that confirms the stack is
 * alive and communicates the product vision to anyone who clones the repo
 * and runs `docker compose up`.
 *
 * The dashboard and all feature screens are built in later phases.
 */

export const metadata: Metadata = {
  title: "RecoverFlow — Phase 0 Foundation",
  description:
    "AI Revenue Recovery Control Plane — stack validation page.",
};

export default function HomePage(): React.JSX.Element {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 py-16 overflow-hidden relative">
      {/* Ambient background glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-brand-600/20 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full bg-brand-800/20 blur-[120px]" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[400px] h-[400px] rounded-full bg-brand-500/10 blur-[80px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 max-w-4xl w-full mx-auto text-center flex flex-col items-center gap-8 animate-fade-in">
        {/* Status badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-300 text-sm font-medium">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-success" />
          </span>
          Phase 0 — Foundation Complete
        </div>

        {/* Wordmark */}
        <div className="flex flex-col items-center gap-2">
          <h1 className="text-display font-bold text-gradient leading-none tracking-tight">
            RecoverFlow
          </h1>
          <p className="text-xl text-text-secondary font-medium">
            AI Revenue Recovery Control Plane
          </p>
        </div>

        {/* Tagline */}
        <p className="max-w-2xl text-lg text-text-secondary leading-relaxed">
          Predicts which failures can be recovered, chooses the safest
          intervention, executes under merchant-defined limits, verifies
          financial outcomes, and measures incremental recovery against a
          baseline.
        </p>

        {/* Metric preview cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full max-w-2xl mt-4">
          <MetricCard
            label="Revenue at Risk"
            value="₹2.47L"
            sublabel="demo dataset"
            color="danger"
          />
          <MetricCard
            label="AI Recoverable"
            value="₹1.82L"
            sublabel="predicted"
            color="warning"
          />
          <MetricCard
            label="Verified Recovery"
            value="₹1.46L"
            sublabel="post-reconciliation"
            color="success"
          />
        </div>

        {/* Architecture flow */}
        <div className="glass-card w-full max-w-2xl p-6 text-left mt-4">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">
            Decision Pipeline
          </h2>
          <div className="flex flex-wrap gap-2 items-center justify-center font-mono text-xs">
            {[
              "Payment Event",
              "→",
              "Risk Firewall",
              "→",
              "ML Predictor",
              "→",
              "Policy Engine",
              "→",
              "Action Layer",
              "→",
              "Finance Truth",
              "→",
              "Audit Log",
            ].map((step, i) => (
              <span
                key={i}
                className={
                  step === "→"
                    ? "text-text-muted"
                    : "px-2.5 py-1 rounded-lg bg-surface-700 border border-surface-600 text-brand-300"
                }
              >
                {step}
              </span>
            ))}
          </div>
        </div>

        {/* Phase status grid */}
        <div className="glass-card w-full max-w-2xl p-6">
          <h2 className="text-sm font-semibold text-text-muted uppercase tracking-wider mb-4">
            Build Progress
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
            <PhaseChip phase="0" label="Foundation" done />
            <PhaseChip phase="1" label="Event Ingestion" />
            <PhaseChip phase="2" label="Data Engine" />
            <PhaseChip phase="3" label="ML Engine" />
            <PhaseChip phase="4" label="Decision Engine" />
            <PhaseChip phase="5" label="LLM Reasoning" />
            <PhaseChip phase="6" label="Risk Firewall" />
            <PhaseChip phase="7" label="Action Layer" />
            <PhaseChip phase="8" label="Finance Truth" />
            <PhaseChip phase="9" label="Dashboard" />
            <PhaseChip phase="10" label="Simulation Lab" />
            <PhaseChip phase="11" label="Failure Center" />
          </div>
        </div>

        {/* Quick links */}
        <div className="flex flex-wrap gap-4 justify-center mt-2">
          <a
            id="leak-graph-link"
            href="/leak-graph"
            className="btn-primary"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
            </svg>
            Revenue Leak Graph
          </a>
          <a
            id="api-docs-link"
            href="/api/docs"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-surface-700 border border-surface-600 text-text-primary font-semibold text-sm hover:bg-surface-600 transition-all duration-200 active:scale-95"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="16" y1="13" x2="8" y2="13" />
              <line x1="16" y1="17" x2="8" y2="17" />
              <polyline points="10 9 9 9 8 9" />
            </svg>
            API Docs
          </a>
          <a
            id="github-link"
            href="https://github.com/RazzGourav/RecoverFlow"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-surface-700 border border-surface-600 text-text-primary font-semibold text-sm hover:bg-surface-600 transition-all duration-200 active:scale-95"
            target="_blank"
            rel="noopener noreferrer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.1 3.29 9.41 7.86 10.94.57.1.78-.25.78-.55v-1.92c-3.2.7-3.87-1.53-3.87-1.53-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.75 1.18 1.75 1.18 1.02 1.74 2.68 1.24 3.33.95.1-.74.4-1.24.73-1.52-2.55-.29-5.23-1.27-5.23-5.67 0-1.25.45-2.27 1.18-3.07-.12-.29-.51-1.45.11-3.02 0 0 .96-.31 3.15 1.17A10.9 10.9 0 0 1 12 6.84c.97 0 1.95.13 2.86.38 2.18-1.48 3.14-1.17 3.14-1.17.62 1.57.23 2.73.11 3.02.73.8 1.18 1.82 1.18 3.07 0 4.41-2.69 5.38-5.25 5.66.41.36.78 1.07.78 2.16v3.2c0 .31.21.66.79.55A11.51 11.51 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5Z" />
            </svg>
            GitHub
          </a>
        </div>

        {/* Build info */}
        <p className="text-xs text-text-muted mt-4">
          Razorpay /buildathon · Track 03 — AI Revenue Recovery ·{" "}
          <span className="text-brand-400">Phase 0 Complete</span>
        </p>
      </div>
    </main>
  );
}

/* ---------------------------------------------------------------------------
   Sub-components (co-located — will be extracted to components/ in Phase 9)
   --------------------------------------------------------------------------- */

interface MetricCardProps {
  label: string;
  value: string;
  sublabel: string;
  color: "danger" | "warning" | "success";
}

function MetricCard({ label, value, sublabel, color }: MetricCardProps): React.JSX.Element {
  const colorMap = {
    danger: "text-danger",
    warning: "text-warning",
    success: "text-success",
  } as const;

  return (
    <div className="metric-card animate-slide-up">
      <span className="metric-label">{label}</span>
      <span className={`metric-value ${colorMap[color]}`}>{value}</span>
      <span className="text-2xs text-text-muted mt-1">{sublabel}</span>
    </div>
  );
}

interface PhaseChipProps {
  phase: string;
  label: string;
  done?: boolean;
}

function PhaseChip({ phase, label, done = false }: PhaseChipProps): React.JSX.Element {
  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm ${
        done
          ? "bg-success/5 border-success/30 text-success"
          : "bg-surface-700/50 border-surface-600/50 text-text-muted"
      }`}
    >
      <span
        className={`text-xs font-mono px-1.5 py-0.5 rounded font-bold ${
          done
            ? "bg-success/20 text-success"
            : "bg-surface-600/80 text-text-muted"
        }`}
      >
        P{phase}
      </span>
      <span className="truncate">{label}</span>
      {done && (
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="ml-auto flex-shrink-0"
          aria-hidden="true"
        >
          <polyline points="20 6 9 17 4 12" />
        </svg>
      )}
    </div>
  );
}
