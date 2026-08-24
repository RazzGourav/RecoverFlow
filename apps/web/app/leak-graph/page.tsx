import type { Metadata } from "next";
import { LeakGraph } from "../components/LeakGraph";

export const metadata: Metadata = {
  title: "Revenue Leak Graph | RecoverFlow",
  description: "Visualize where revenue leaks occur across the customer funnel.",
};

export default function LeakGraphPage(): React.JSX.Element {
  return (
    <div className="p-8 max-w-[1600px] mx-auto w-full">
      
      <header className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-white/90">Revenue Leak Graph</h1>
        <p className="text-white/50 text-sm mt-1">End-to-end visualization of funnel drop-offs and AI recovery impact.</p>
      </header>

      <div className="relative z-10 w-full">
        <LeakGraph />
      </div>

    </div>
  );
}
