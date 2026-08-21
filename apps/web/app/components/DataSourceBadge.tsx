/**
 * DataSourceBadge — Reusable honesty label component (Phase 9 requirement).
 *
 * Why: Every place synthetic vs live data surfaces in the UI must be
 * honestly labeled. This badge component ensures consistent, permanent
 * labeling without manual effort per screen.
 */

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
