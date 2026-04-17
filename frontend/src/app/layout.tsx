import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "KM Curve Analyzer",
  description: "Extract survival data from Kaplan-Meier curves and compute log-rank tests",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav className="bg-white border-b border-slate-200 px-6 py-3 flex items-center gap-6">
          <span className="font-bold text-primary text-lg">KM Analyzer</span>
          <a href="/" className="text-sm text-slate-600 hover:text-primary">Analyze</a>
          <a href="/indirect" className="text-sm text-slate-600 hover:text-primary">Indirect Comparison</a>
        </nav>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
