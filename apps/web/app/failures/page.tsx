"use client";

import { useEffect, useState } from "react";
import { fetchAuditFailures } from "./actions";
import { formatDistanceToNow } from "date-fns";

export default function FailuresPage() {
  const [events, setEvents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadFailures() {
      try {
        const data = await fetchAuditFailures();
        setEvents(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load failures");
      } finally {
        setLoading(false);
      }
    }
    loadFailures();
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-b-2 border-t-2 border-red-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-900/20 p-6 text-center text-red-400">
        <h3 className="text-lg font-semibold">Error Loading Failures</h3>
        <p className="mt-2">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 fill-mode-both">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Failure Center</h1>
          <p className="text-muted-foreground mt-2">
            Real-time feed of dropped, blocked, and failed system events.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg bg-red-950/30 px-4 py-2 border border-red-900/50">
          <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse"></div>
          <span className="text-sm font-medium text-red-200">Live Monitoring</span>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-card shadow-sm">
        <div className="p-6 overflow-x-auto">
          <table className="w-full text-left text-sm text-muted-foreground">
            <thead className="text-xs uppercase bg-muted/50 text-muted-foreground border-b border-border">
              <tr>
                <th className="px-4 py-3">Timestamp</th>
                <th className="px-4 py-3">Event Type</th>
                <th className="px-4 py-3">Case ID</th>
                <th className="px-4 py-3">Reason / Context</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {events.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center">
                    No failure events found. System is stable.
                  </td>
                </tr>
              ) : (
                events.map((evt) => (
                  <tr key={evt.id} className="hover:bg-muted/50 transition-colors">
                    <td className="px-4 py-4 whitespace-nowrap text-foreground">
                      {formatDistanceToNow(new Date(evt.timestamp), { addSuffix: true })}
                    </td>
                    <td className="px-4 py-4">
                      <span className="inline-flex items-center rounded-md bg-red-900/30 px-2 py-1 text-xs font-medium text-red-300 ring-1 ring-inset ring-red-900/50">
                        {evt.event_type}
                      </span>
                    </td>
                    <td className="px-4 py-4 font-mono text-xs">
                      {evt.case_id ? evt.case_id.split("-")[0] : "N/A"}
                    </td>
                    <td className="px-4 py-4">
                      <div className="max-w-md truncate text-foreground font-medium">
                        {evt.reason || "System dropped event."}
                      </div>
                      {evt.context && (
                        <div className="mt-1 text-xs text-muted-foreground font-mono">
                          {JSON.stringify(evt.context)}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
