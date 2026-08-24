"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { 
  LayoutDashboard, 
  Briefcase, 
  Activity, 
  ShieldAlert, 
  Settings2, 
  History, 
  FlaskConical
} from "lucide-react";
import { cn } from "./utils";

const navItems = [
  { name: "Control Tower", href: "/", icon: LayoutDashboard },
  { name: "Recovery Cases", href: "/cases", icon: Briefcase },
  { name: "Leak Graph", href: "/leak-graph", icon: Activity },
  { name: "Failure Center", href: "/failures", icon: ShieldAlert },
  { name: "Simulation Lab", href: "/simulation", icon: FlaskConical },
  { name: "Policy Studio", href: "/policies", icon: Settings2 },
  { name: "Audit Explorer", href: "/audit", icon: History },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="w-64 flex-shrink-0 h-screen sticky top-0 bg-[#0b1326]/80 backdrop-blur-3xl border-r border-white/5 flex flex-col pt-8 pb-4">
      <div className="px-6 mb-8 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-[#06b6d4] to-[#d946ef] flex items-center justify-center shadow-[0_0_15px_rgba(217,70,239,0.4)]">
          <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
        </div>
        <span className="text-xl font-bold tracking-tight text-white">Recover<span className="text-white/60">Flow</span></span>
      </div>

      <nav className="flex-1 px-4 flex flex-col gap-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link 
              key={item.href} 
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-300",
                isActive 
                  ? "text-white" 
                  : "text-white/50 hover:text-white hover:bg-white/5"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="active-nav"
                  className="absolute inset-0 bg-white/10 rounded-xl"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              {/* Highlight line on the left */}
              {isActive && (
                <motion.div
                  layoutId="active-indicator"
                  className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-gradient-to-b from-[#06b6d4] to-[#d946ef] rounded-r-full"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              
              <item.icon className={cn("w-5 h-5 relative z-10 transition-colors", isActive ? "text-[#06b6d4]" : "group-hover:text-white")} />
              <span className="relative z-10 font-medium text-sm">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="px-6 mt-auto">
        <div className="bg-[#1e1b4b]/40 border border-[#d946ef]/20 rounded-xl p-4 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-[100px] h-[100px] bg-[#d946ef]/10 rounded-full blur-[40px] pointer-events-none" />
          <p className="text-xs text-white/50 mb-1">System Status</p>
          <div className="flex items-center gap-2">
            <span className="relative flex h-2.5 w-2.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#06b6d4] opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-[#06b6d4]"></span>
            </span>
            <span className="text-sm font-medium text-[#06b6d4]">AI Active</span>
          </div>
        </div>
      </div>
    </div>
  );
}
