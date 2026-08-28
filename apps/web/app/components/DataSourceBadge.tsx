/**
 * DataSourceBadge — Reusable honesty label component (Phase 9 requirement).
 *
 * Why: Every place synthetic vs live data surfaces in the UI must be
 * honestly labeled. This badge component ensures consistent, permanent
 * labeling without manual effort per screen.
 *
 * Also surfaces the payment provider mode (mock / razorpay) so operators
 * can immediately see whether they are looking at simulated or real payment
 * activity — a PRD requirement for transparency during the demo.
 */

import React from "react";

interface DataSourceBadgeProps {
  source: "simulated" | "live";
}

export function DataSourceBadge({ source }: DataSourceBadgeProps): React.JSX.Element {
  if (source === "simulated") {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-medium bg-warning/10 text-warning border border-warning/30">
        <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        Simulated traffic data
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-2xs font-medium bg-success/10 text-success border border-success/30">
      <span className="relative flex h-1.5 w-1.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-success" />
      </span>
      Live system data
    </span>
  );
}

// ─── Payment Provider Badge ──────────────────────────────────────────────────

type ProviderMode = "mock" | "razorpay";

interface ProviderBadgeProps {
  /** Payment provider mode. Defaults to NEXT_PUBLIC_PAYMENT_PROVIDER env var. */
  provider?: ProviderMode;
}

/**
 * ProviderBadge — Surfaces the active payment provider mode.
 *
 * Why: AGENTS.md (Rule 5) requires that any MockProvider usage is clearly
 * labeled in the UI so operators never mistake simulated payment activity for
 * real money movement. Reuses the same amber/warning visual language as
 * DataSourceBadge so the two honesty labels feel like a system, not ad-hoc.
 *
 * Reads NEXT_PUBLIC_PAYMENT_PROVIDER at build time (set in next.config.mjs
 * from the PAYMENT_PROVIDER .env variable), so it correctly reflects
 * whichever mode is active without any additional API call.
 */
export function ProviderBadge({ provider }: ProviderBadgeProps): React.JSX.Element {
  const mode: ProviderMode =
    (provider as ProviderMode) ??
    ((process.env.NEXT_PUBLIC_PAYMENT_PROVIDER ?? "mock") as ProviderMode);

  const isMock = mode !== "razorpay";

  if (isMock) {
    return (
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30"
        title="Actions use the MockProvider — no real money is moved"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="11"
          height="11"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        Payment Provider: Mock (Test Mode)
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30"
      title="Actions use the live Razorpay Test Mode — real API calls, no real money"
    >
      <span className="relative flex h-1.5 w-1.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
        <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-blue-400" />
      </span>
      Payment Provider: Razorpay (Test Mode)
    </span>
  );
}
