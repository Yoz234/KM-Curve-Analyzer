"use client";

import { useState } from "react";
import DropZone from "@/components/DropZone";
import KMChart from "@/components/KMChart";
import ResultCard from "@/components/ResultCard";
import ApiKeyBanner from "@/components/ApiKeyBanner";
import PubmedFigurePicker from "@/components/PubmedFigurePicker";
import KMAnalysisFlow, { type Source } from "@/components/KMAnalysisFlow";
import { type AnalyzeResponse } from "@/lib/api";
import { DEMO_CASES } from "@/lib/demoData";
import clsx from "clsx";

type Mode = "upload" | "pubmed";

export default function HomePage() {
  const [mode, setMode] = useState<Mode>("upload");
  const [source, setSource] = useState<Source>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState("");

  function handleFile(f: File) {
    setSource({ file: f });
    setPreview(URL.createObjectURL(f));
    setResult(null);
    setError("");
  }

  function handleUrl(url: string) {
    const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    setSource({ url });
    setPreview(`${BASE}/api/proxy-image?url=${encodeURIComponent(url)}`);
    setResult(null);
    setError("");
  }

  function handleDemo(id: string) {
    const demo = DEMO_CASES.find((d) => d.id === id);
    if (!demo) return;
    setSource({ extraction: demo.extraction, label: demo.label });
    setPreview(null);
    setResult(null);
    setError("");
    // scroll to analysis flow
    setTimeout(() => {
      document.getElementById("analysis-flow")?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">KM Curve Analyzer</h1>
        <p className="text-slate-500 text-sm mt-1">
          Upload a Kaplan-Meier figure or try a demo — LLM extracts the data, then we compute
          log-rank statistics and hazard ratios.
        </p>
      </div>

      {/* Demo cards — no API key needed */}
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          Try a demo (no API key required)
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {DEMO_CASES.map((demo) => (
            <button
              key={demo.id}
              onClick={() => handleDemo(demo.id)}
              className={clsx(
                "text-left rounded-xl border p-4 transition-all",
                source && "extraction" in source && (source as { label: string }).label === demo.label
                  ? "border-primary bg-blue-50 ring-1 ring-primary"
                  : "border-slate-200 bg-white hover:border-slate-400 hover:shadow-sm"
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {demo.badge}
                </span>
                <span className="text-xs text-slate-400">{demo.trial}</span>
              </div>
              <p className="font-semibold text-slate-800 text-sm">{demo.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{demo.description}</p>
              <p className="text-xs text-slate-400 mt-1">
                Published HR: <span className="font-mono">{demo.published_hr}</span>
              </p>
            </button>
          ))}
        </div>
      </div>

      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden>
          <div className="w-full border-t border-slate-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-slate-50 px-3 text-xs text-slate-400">or analyze your own figure</span>
        </div>
      </div>

      <ApiKeyBanner />

      {/* Mode tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {(["upload", "pubmed"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => { setMode(m); setSource(null); setResult(null); setError(""); setPreview(null); }}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              mode === m
                ? "border-primary text-primary"
                : "border-transparent text-slate-500 hover:text-slate-800"
            )}
          >
            {m === "upload" ? "Upload Image" : "Search PubMed"}
          </button>
        ))}
      </div>

      {mode === "upload" && <DropZone onFile={handleFile} />}
      {mode === "pubmed" && (
        <PubmedFigurePicker onUrl={handleUrl} onFile={handleFile} analyzing={loading} />
      )}

      {/* Two-step analysis flow */}
      <div id="analysis-flow">
        <KMAnalysisFlow
          source={source}
          onResult={setResult}
          onError={setError}
          onLoadingChange={setLoading}
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <strong>Error:</strong> {error}
        </div>
      )}

      {(preview || result) && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {preview && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-2 font-medium">Original Figure</p>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={preview} alt="KM figure" className="w-full object-contain max-h-72" />
            </div>
          )}
          {result && (
            <div className="bg-white rounded-xl border border-slate-200 p-4">
              <p className="text-xs text-slate-500 mb-2 font-medium">Extraction Summary</p>
              <div className="space-y-2 text-sm">
                <p><span className="text-slate-500">Title:</span> {result.extraction.title || "—"}</p>
                <p><span className="text-slate-500">Time unit:</span> {result.extraction.x_axis?.unit ?? "—"}</p>
                <p><span className="text-slate-500">Groups detected:</span> {result.extraction.n_groups}</p>
                {result.groups.map((g) => (
                  <div key={g.name} className="flex gap-4 bg-slate-50 rounded px-3 py-1">
                    <span className="font-medium">{g.name}</span>
                    <span className="text-slate-500">N={g.n}</span>
                    <span className="text-slate-500">Events={g.n_events}</span>
                  </div>
                ))}
                {result.extraction.extraction_notes && (
                  <p className="text-xs text-amber-700 bg-amber-50 rounded p-2 mt-1">
                    Note: {result.extraction.extraction_notes}
                  </p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {result && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs text-slate-500 mb-2 font-medium">Reconstructed KM Curves (from extracted data)</p>
          <KMChart
            curves={result.logrank.km_curves}
            xLabel={result.extraction.x_axis?.label ?? "Time"}
            medians={result.logrank.median_survival}
          />
        </div>
      )}

      {result && <ResultCard result={result.logrank} />}
    </div>
  );
}
