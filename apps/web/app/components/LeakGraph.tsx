"use client";

/**
 * LeakGraph — Revenue Leak Graph visualization (Phase 9.5).
 *
 * Why: Displays the full funnel from visitors → payment with
 * stage counts, ₹ values, drop-off rates, and drill-through
 * at each leak point.
 *
 * Uses Recharts BarChart for the funnel visualization — a proven,
 * lightweight library instead of hand-rolling sankey math.
 */

import { useEffect, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { DataSourceBadge } from "./DataSourceBadge";

// ---------------------------------------------------------------------------
// Types (mirror the API response shape)
// ---------------------------------------------------------------------------

interface RootCauseBreakdown {
  failure_type: string;
  count: number;
  revenue_at_risk_paise: number;
}

interface SegmentBreakdown {
  segment: string;
  count: number;
}

interface RecoveryActionSummary {
  action_type: string;
  count: number;
  total_expected_recovery_paise: number;
}

interface LeakPoint {
  from_stage: string;
  to_stage: string;
  lost_count: number;
  lost_value_paise: number;
  root_causes: RootCauseBreakdown[];
  affected_segments: SegmentBreakdown[];
  recovery_actions: RecoveryActionSummary[];
}

interface FunnelStage {
  stage: string;
  count: number;
  value_paise: number;
  data_source: "simulated" | "live";
}

export interface LeakGraphData {
  stages: FunnelStage[];
  leaks: LeakPoint[];
  generated_at: string;
  note: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const STAGE_LABELS: Record<string, string> = {
  SITE_VISIT: "Site Visits",
  PRODUCT_VIEW: "Product Views",
  ADD_TO_CART: "Add to Cart",
  CHECKOUT_STARTED: "Checkout",
  PAYMENT_ATTEMPTED: "Payment Attempts",
  PAYMENT_SUCCESSFUL: "Successful",
};

const STAGE_COLORS: Record<string, string> = {
  SITE_VISIT: "#6366f1",
  PRODUCT_VIEW: "#8b5cf6",
  ADD_TO_CART: "#a78bfa",
  CHECKOUT_STARTED: "#f59e0b",
  PAYMENT_ATTEMPTED: "#ef4444",
  PAYMENT_SUCCESSFUL: "#22c55e",
};

function formatPaise(paise: number): string {
  const rupees = paise / 100;
  if (rupees >= 100000) return `₹${(rupees / 100000).toFixed(2)}L`;
  if (rupees >= 1000) return `₹${(rupees / 1000).toFixed(1)}K`;
  return `₹${rupees.toFixed(0)}`;
}

function formatCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`;
  return n.toString();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function LeakGraph({ initialData }: { initialData?: LeakGraphData | null } = {}): React.JSX.Element {
  const [data, setData] = useState<LeakGraphData | null>(initialData || null);
  const [loading, setLoading] = useState(!initialData);
  const [error, setError] = useState<string | null>(null);
  const [selectedLeak, setSelectedLeak] = useState<LeakPoint | null>(null);

  useEffect(() => {
    if (initialData) return;
    fetch("/api/leak-graph")
      .then((r) => {
        if (!r.ok) throw new Error(`API error: ${r.status}`);
        return r.json();
      })
      .then((d: LeakGraphData) => {
        setData(d);
        setLoading(false);
      })
      .catch((e: Error) => {
        setError(e.message);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="glass-card p-8 text-center">
        <div className="animate-pulse text-text-muted">Loading Revenue Leak Graph...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-card p-8 text-center">
        <div className="text-danger">Failed to load: {error}</div>
      </div>
    );
  }

  const chartData = data.stages.map((s) => ({
    name: STAGE_LABELS[s.stage] || s.stage,
    count: s.count,
    value: s.value_paise,
    stage: s.stage,
    source: s.data_source,
  }));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-text-primary">Revenue Leak Graph</h2>
          <p className="text-sm text-text-muted mt-1">{data.note}</p>
        </div>
        <div className="flex gap-2">
          <DataSourceBadge source="simulated" />
          <DataSourceBadge source="live" />
        </div>
      </div>

      {/* Funnel Bar Chart */}
      <div className="glass-card p-6">
        <ResponsiveContainer width="100%" height={340}>
          <BarChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 12 }} />
            <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #334155",
                borderRadius: "8px",
                color: "#f1f5f9",
              }}
              formatter={(value: number, name: string) => [
                formatCount(value),
                name === "count" ? "Sessions" : "Value",
              ]}
              labelFormatter={(label: string) => label}
            />
            <Bar dataKey="count" radius={[6, 6, 0, 0]} cursor="pointer">
              {chartData.map((entry, idx) => (
                <Cell
                  key={`cell-${idx}`}
                  fill={STAGE_COLORS[entry.stage] || "#6366f1"}
                  opacity={0.85}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Stage cards with leak points */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.stages.map((stage, idx) => {
          const leak = data.leaks.find((l) => l.from_stage === stage.stage);
          const dropRate =
            idx > 0 && data.stages[idx - 1].count > 0
              ? (
                  ((data.stages[idx - 1].count - stage.count) /
                    data.stages[idx - 1].count) *
                  100
                ).toFixed(1)
              : null;

          return (
            <div
              key={stage.stage}
              id={`stage-${stage.stage.toLowerCase()}`}
              className="glass-card p-4 relative group"
            >
              <div className="flex items-start justify-between mb-2">
                <h3 className="text-sm font-semibold text-text-primary">
                  {STAGE_LABELS[stage.stage] || stage.stage}
                </h3>
                <DataSourceBadge source={stage.data_source} />
              </div>

              <div className="text-2xl font-bold text-text-primary">
                {formatCount(stage.count)}
              </div>
              <div className="text-sm text-text-muted">
                {formatPaise(stage.value_paise)} revenue
              </div>

              {dropRate && (
                <div className="mt-2 text-xs text-danger">
                  ↓ {dropRate}% drop-off from previous stage
                </div>
              )}

              {/* Leak drill-through button */}
              {leak && leak.lost_count > 0 && (
                <button
                  onClick={() => setSelectedLeak(leak)}
                  className="mt-3 w-full text-xs px-3 py-1.5 rounded-lg bg-danger/10 border border-danger/30 text-danger hover:bg-danger/20 transition-colors"
                >
                  🔍 {formatCount(leak.lost_count)} lost →{" "}
                  {STAGE_LABELS[leak.to_stage]} ({formatPaise(leak.lost_value_paise)})
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Drill-through panel */}
      {selectedLeak && (
        <div className="glass-card p-6 border-l-4 border-danger animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-text-primary">
              Leak: {STAGE_LABELS[selectedLeak.from_stage]} →{" "}
              {STAGE_LABELS[selectedLeak.to_stage]}
            </h3>
            <button
              onClick={() => setSelectedLeak(null)}
              className="text-text-muted hover:text-text-primary text-sm"
            >
              ✕ Close
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
            <div>
              <div className="text-text-muted mb-1 uppercase text-xs font-semibold tracking-wider">
                Lost
              </div>
              <div className="text-2xl font-bold text-danger">
                {formatCount(selectedLeak.lost_count)} sessions
              </div>
              <div className="text-danger/70">
                {formatPaise(selectedLeak.lost_value_paise)} revenue at risk
              </div>
            </div>

            {/* Root Causes */}
            {selectedLeak.root_causes.length > 0 && (
              <div>
                <div className="text-text-muted mb-2 uppercase text-xs font-semibold tracking-wider">
                  Root Causes
                </div>
                {selectedLeak.root_causes.map((rc) => (
                  <div
                    key={rc.failure_type}
                    className="flex justify-between py-1 border-b border-surface-700"
                  >
                    <span className="text-text-secondary">{rc.failure_type}</span>
                    <span className="text-text-primary font-mono">
                      {rc.count} ({formatPaise(rc.revenue_at_risk_paise)})
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Segments */}
            {selectedLeak.affected_segments.length > 0 && (
              <div>
                <div className="text-text-muted mb-2 uppercase text-xs font-semibold tracking-wider">
                  Affected Segments
                </div>
                {selectedLeak.affected_segments.map((seg) => (
                  <div
                    key={seg.segment}
                    className="flex justify-between py-1 border-b border-surface-700"
                  >
                    <span className="text-text-secondary">{seg.segment}</span>
                    <span className="text-text-primary font-mono">{seg.count}</span>
                  </div>
                ))}
              </div>
            )}

            {/* Recovery Actions */}
            {selectedLeak.recovery_actions.length > 0 && (
              <div>
                <div className="text-text-muted mb-2 uppercase text-xs font-semibold tracking-wider">
                  Recovery Actions
                </div>
                {selectedLeak.recovery_actions.map((ra) => (
                  <div
                    key={ra.action_type}
                    className="flex justify-between py-1 border-b border-surface-700"
                  >
                    <span className="text-text-secondary">{ra.action_type}</span>
                    <span className="text-success font-mono">
                      {ra.count}× ({formatPaise(ra.total_expected_recovery_paise)})
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
