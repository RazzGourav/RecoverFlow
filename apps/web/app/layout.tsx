import type { Metadata } from "next";
import "./globals.css";

/**
 * RecoverFlow root layout.
 *
 * Why: Next.js App Router requires a root layout that wraps all pages.
 * This is where global metadata, fonts (via Google Fonts CSS import in
 * globals.css), and any providers are mounted exactly once.
 */

export const metadata: Metadata = {
  title: {
    template: "%s | RecoverFlow",
    default: "RecoverFlow — AI Revenue Recovery Control Plane",
  },
  description:
    "RecoverFlow turns payment failure from a reactive operations problem into an " +
    "intelligent, measurable and governed revenue-optimization loop.",
  keywords: [
    "revenue recovery",
    "payment failure",
    "AI",
    "Razorpay",
    "subscription",
    "fintech",
  ],
  authors: [{ name: "RecoverFlow Team" }],
  openGraph: {
    type: "website",
    title: "RecoverFlow — AI Revenue Recovery Control Plane",
    description:
      "Predicts which failures can be recovered and chooses the best next action.",
    siteName: "RecoverFlow",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.JSX.Element {
  return (
    <html lang="en" className="dark">
      <body className="bg-surface-900 text-text-primary antialiased">
        {children}
      </body>
    </html>
  );
}
