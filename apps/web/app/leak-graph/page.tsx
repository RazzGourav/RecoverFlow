import type { Metadata } from "next";
import { LeakGraph } from "../components/LeakGraph";

/**
 * Revenue Leak Graph page (Phase 9.5).
 *
 * Why: Provides a dedicated page for the Revenue Leak Graph visualization,
 * showing the full top-of-funnel through payment-stage funnel with
 * drill-through capabilities at each leak point.
 */

export const metadata: Metadata = {
  title: "Revenue Leak Graph",
  description:
    "Visualize where revenue leaks occur across the customer funnel — from visits through payment — with root-cause drill-through.",
};

export default function LeakGraphPage(): React.JSX.Element {
  return (
    <main className="min-h-screen px-4 py-8 sm:px-8 relative">
      {/* Ambient background glow */}
      <div
        aria-hidden="true"
        className="pointer-events-none fixed inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-brand-600/20 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 w-[600px] h-[600px] rounded-full bg-brand-800/20 blur-[120px]" />
      </div>

      <div className="relative z-10 max-w-6xl mx-auto space-y-6">
        {/* Nav */}
        <nav className="flex items-center gap-4">
          <a
            href="/"
            className="text-sm text-text-muted hover:text-text-primary transition-colors"
          >
            ← Home
          </a>
          <span className="text-text-muted">/</span>
          <span className="text-sm text-brand-300 font-medium">
            Revenue Leak Graph
          </span>
        </nav>

        <LeakGraph />
      </div>
    </main>
  );
}
