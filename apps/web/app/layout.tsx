import type { Metadata } from "next";
import "./globals.css";
import { Sidebar } from "./components/Sidebar";

/**
 * RecoverFlow root layout.
 */

export const metadata: Metadata = {
  title: {
    template: "%s | RecoverFlow",
    default: "RecoverFlow — AI Revenue Recovery Control Plane",
  },
  description:
    "RecoverFlow turns payment failure from a reactive operations problem into an intelligent, measurable and governed revenue-optimization loop.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <html lang="en" className="dark">
      <body className="bg-[#0b1326] text-white antialiased flex min-h-screen selection:bg-brand-500/30">
        <Sidebar />
        <main className="flex-1 min-w-0 relative">
          <div className="absolute inset-0 pointer-events-none overflow-hidden z-0">
            <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#581c87]/10 rounded-full blur-[100px]" />
            <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[#0f172a]/40 rounded-full blur-[120px]" />
          </div>
          <div className="relative z-10 w-full">
            {children}
          </div>
        </main>
      </body>
    </html>
  );
}
