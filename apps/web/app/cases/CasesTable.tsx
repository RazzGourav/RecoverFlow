"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowUpDown, Search, Filter, AlertTriangle, CheckCircle2, AlertCircle, Clock, ShieldAlert, User, ShieldCheck } from "lucide-react";
import { cn } from "../components/utils";

type Case = {
  id: string;
  created_at: string;
  amount_paise: number;
  customer_segment: string;
  failure_type: string;
  risk_level: string;
  status: string;
  expected_recovery_paise?: number | null;
};

export function CasesTable({ initialCases }: { initialCases: Case[] }) {
  const [filter, setFilter] = useState<string>("ALL");
  const [sortField, setSortField] = useState<"created_at" | "amount_paise" | "expected_recovery">("created_at");
  const [sortDesc, setSortDesc] = useState(true);

  const filteredCases = useMemo(() => {
    return initialCases.filter(c => {
      if (filter === "ALL") return true;
      if (filter === "HIGH_VALUE") return c.amount_paise > 1000000; // > 10,000 INR
      if (filter === "HIGH_RISK") return c.risk_level === "HIGH";
      if (filter === "PENDING") return c.status === "PENDING" || c.status === "EXECUTING";
      if (filter === "BLOCKED") return c.status === "BLOCKED" || c.status === "UNRECOVERABLE";
      if (filter === "RECOVERED") return c.status === "RECOVERED";
      if (filter === "HUMAN_REVIEW") return c.status === "HUMAN_REVIEW";
      return true;
    });
  }, [initialCases, filter]);

  const sortedCases = useMemo(() => {
    /**
     * Returns a numeric sort key for the given case and sort field.
     * Null/undefined expected_recovery_paise maps to -Infinity so nulls
     * always sort to the bottom (after real values) in both asc and desc order.
     * For date fields we use getTime(); for numeric fields the raw paise value.
     */
    const getSortValue = (c: Case, field: typeof sortField): number => {
      if (field === "expected_recovery") {
        const v = c.expected_recovery_paise;
        return v != null ? v : -Infinity;
      }
      if (field === "amount_paise") {
        return c.amount_paise;
      }
      // field === "created_at"
      return new Date(c.created_at).getTime();
    };

    return [...filteredCases].sort((a, b) => {
      const valA = getSortValue(a, sortField);
      const valB = getSortValue(b, sortField);

      // Nulls (represented as -Infinity) always sort to the bottom
      if (valA === -Infinity && valB !== -Infinity) return 1;
      if (valA !== -Infinity && valB === -Infinity) return -1;
      if (valA === -Infinity && valB === -Infinity) return 0;

      if (valA < valB) return sortDesc ? 1 : -1;
      if (valA > valB) return sortDesc ? -1 : 1;
      return 0;
    });
  }, [filteredCases, sortField, sortDesc]);

  const handleSort = (field: typeof sortField) => {
    if (sortField === field) {
      setSortDesc(!sortDesc);
    } else {
      setSortField(field);
      setSortDesc(true);
    }
  };

  const filters = [
    { id: "ALL", label: "All Cases", icon: Filter },
    { id: "HIGH_VALUE", label: "High Value", icon: AlertTriangle },
    { id: "HIGH_RISK", label: "High Risk", icon: ShieldAlert },
    { id: "PENDING", label: "Pending", icon: Clock },
    { id: "BLOCKED", label: "Blocked", icon: AlertCircle },
    { id: "RECOVERED", label: "Recovered", icon: CheckCircle2 },
    { id: "HUMAN_REVIEW", label: "Human Review", icon: User },
  ];

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex flex-wrap gap-2">
        {filters.map(f => (
          <button
            key={f.id}
            onClick={() => setFilter(f.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300",
              filter === f.id 
                ? "bg-brand-500/20 border border-brand-500/40 text-brand-300 shadow-[0_0_15px_rgba(217,70,239,0.2)]" 
                : "bg-white/5 border border-white/10 text-white/60 hover:text-white/90 hover:bg-white/10"
            )}
          >
            <f.icon className="w-4 h-4" />
            {f.label}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="bg-[#1e1b4b]/40 backdrop-blur-2xl rounded-2xl border border-white/5 overflow-hidden shadow-2xl relative">
        <div className="absolute top-0 right-1/4 w-[300px] h-[300px] bg-brand-500/5 rounded-full blur-[80px] pointer-events-none" />
        
        <div className="overflow-x-auto relative z-10">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-black/20 text-white/50 border-b border-white/10 uppercase text-xs font-semibold tracking-wider">
              <tr>
                <th className="px-6 py-4">Case ID</th>
                <th className="px-6 py-4 cursor-pointer hover:text-white/80 transition-colors" onClick={() => handleSort('created_at')}>
                  <div className="flex items-center gap-1">Created At <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4 cursor-pointer hover:text-white/80 transition-colors" onClick={() => handleSort('amount_paise')}>
                  <div className="flex items-center gap-1">Amount <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">Risk Level</th>
                <th className="px-6 py-4 text-right cursor-pointer hover:text-white/80 transition-colors text-brand-300" onClick={() => handleSort('expected_recovery')}>
                  <div className="flex items-center justify-end gap-1">Expected Recovery <ArrowUpDown className="w-3 h-3" /></div>
                </th>
                <th className="px-6 py-4 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              <AnimatePresence initial={false}>
                {sortedCases.map((c) => (
                  <motion.tr 
                    key={c.id} 
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="hover:bg-white/[0.03] transition-colors group"
                  >
                    <td className="px-6 py-4">
                      <Link href={`/cases/${c.id}`} className="text-brand-400 font-semibold group-hover:text-brand-300 group-hover:underline flex items-center gap-2">
                        {c.id.split("-")[0]}...
                      </Link>
                    </td>
                    <td className="px-6 py-4 text-white/50">
                      {new Date(c.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td className="px-6 py-4 font-semibold text-white/90">
                      ₹{(c.amount_paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                    </td>
                    <td className="px-6 py-4 text-white/70">
                      {c.customer_segment || "UNKNOWN"}
                    </td>
                    <td className="px-6 py-4">
                      {c.risk_level === "HIGH" ? (
                        <span className="flex items-center gap-1 text-rose-400 font-semibold text-xs bg-rose-500/10 px-2 py-1 rounded-md w-max">
                          <ShieldAlert className="w-3 h-3" /> {c.risk_level}
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-emerald-400/70 font-medium text-xs bg-emerald-500/10 px-2 py-1 rounded-md w-max">
                          <ShieldCheck className="w-3 h-3" /> {c.risk_level || "LOW"}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right font-bold text-emerald-300 filter drop-shadow-[0_0_5px_rgba(52,211,153,0.3)]">
                      {c.expected_recovery_paise != null ? (
                        `₹${(c.expected_recovery_paise / 100).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
                      ) : (
                        <span className="text-white/40 font-normal italic">Pending</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <span className={cn("px-3 py-1 rounded-full text-[11px] font-bold tracking-wider border", getStatusColor(c.status))}>
                        {c.status}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </AnimatePresence>
              {sortedCases.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-16 text-center text-white/30">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <Search className="w-8 h-8 opacity-50" />
                      <p>No cases found matching the criteria.</p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function getStatusColor(status: string) {
  switch (status) {
    case 'RECOVERED': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
    case 'PENDING': 
    case 'EXECUTING': return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
    case 'HUMAN_REVIEW': return 'bg-orange-500/10 text-orange-400 border-orange-500/30';
    case 'FAILED': 
    case 'UNRECOVERABLE':
    case 'BLOCKED': return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    default: return 'bg-white/5 text-white/60 border-white/10';
  }
}
