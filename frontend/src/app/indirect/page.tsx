"use client";

import { useState } from "react";
import { analyzeKM, indirectComparison, type AnalyzeResponse, type IndirectResult } from "@/lib/api";
import DropZone from "@/components/DropZone";
import KMChart from "@/components/KMChart";
import ApiKeyBanner from "@/components/ApiKeyBanner";
import PubmedFigurePicker from "@/components/PubmedFigurePicker";
import KMAnalysisFlow from "@/components/KMAnalysisFlow";
import clsx from "clsx";

type Mode = "upload" | "pubmed";
type Step = "idle" | "loading_ab" | "loading_bc" | "loading_indirect" | "done" | "error";

interface HRInput { hr: string; lower: string; upper: string }

// ---------------------------------------------------------------------------
// Per-slot state for PubMed mode: figure selection → KM analysis → HR
// ---------------------------------------------------------------------------

type SlotSource = { file: File } | { url: string } | null;

interface ArticleSlotProps {
  label: string;
  onHR: (hr: HRInput) => void;
}

function ArticleSlot({ label, onHR }: ArticleSlotProps) {
  const [source, setSource] = useState<SlotSource>(null);
  const [loading, setLoading] = useState(false);
  const [hr, setHr] = useState<HRInput | null>(null);
  const [err, setErr] = useState("");

  function handleResult(res: AnalyzeResponse) {
    const h = res.logrank.hazard_ratio;
    if (!h.value) { setErr("Could not compute HR from this figure."); return; }
    const extracted: HRInput = {
      hr: String(h.value),
      lower: String(h.ci_lower ?? ""),
      upper: String(h.ci_upper ?? ""),
    };
    setHr(extracted);
    onHR(extracted);
  }

  function handleNewSource(src: SlotSource) {
    setSource(src);
    setHr(null);
    setErr("");
  }

  return (
    <div className="border border-slate-200 rounded-xl p-4 space-y-3">
      <PubmedFigurePicker
        label={label}
        onUrl={(url) => handleNewSource({ url })}
        onFile={(file) => handleNewSource({ file })}
        analyzing={loading}
      />

      <KMAnalysisFlow
        source={source}
        onResult={handleResult}
        onError={setErr}
        onLoadingChange={setLoading}
      />

      {err && <p className="text-xs text-red-500">{err}</p>}
      {hr && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-xs text-green-800">
          HR extracted: <span className="font-mono font-medium">
            {hr.hr} (CI {hr.lower}–{hr.upper})
          </span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function IndirectPage() {
  const [mode, setMode] = useState<Mode>("pubmed");

  const [labelA, setLabelA] = useState("A");
  const [labelB, setLabelB] = useState("B");
  const [labelC, setLabelC] = useState("C");

  // Upload mode state
  const [fileAB, setFileAB] = useState<File | null>(null);
  const [fileBC, setFileBC] = useState<File | null>(null);
  const [resultAB, setResultAB] = useState<AnalyzeResponse | null>(null);
  const [resultBC, setResultBC] = useState<AnalyzeResponse | null>(null);

  // PubMed mode extracted HRs
  const [hrAB, setHrAB] = useState<HRInput | null>(null);
  const [hrBC, setHrBC] = useState<HRInput | null>(null);

  // Demo pre-fill indicator
  const [demoLoaded, setDemoLoaded] = useState(false);

  const [step, setStep] = useState<Step>("idle");
  const [indirect, setIndirect] = useState<IndirectResult | null>(null);
  const [error, setError] = useState("");

  const loading = ["loading_ab", "loading_bc", "loading_indirect"].includes(step);

  function handleLoadDemo() {
    // Published values:
    //   FRESCO (Li 2018 JAMA): Fruquintinib vs Placebo, OS HR=0.57 (0.45–0.73)
    //   CORRECT (Grothey 2013 Lancet): Regorafenib vs Placebo, OS HR=0.77 (0.64–0.94)
    //     -> Placebo vs Regorafenib = 1/0.77=1.30 (CI: 1/0.94=1.06, 1/0.64=1.56)
    setLabelA("Fruquintinib");
    setLabelB("Placebo");
    setLabelC("Regorafenib");
    setHrAB({ hr: "0.57", lower: "0.45", upper: "0.73" });
    setHrBC({ hr: "1.30", lower: "1.06", upper: "1.56" });
    setDemoLoaded(true);
    setIndirect(null);
    setError("");
    setStep("idle");
    setMode("pubmed");
  }

  async function handleUploadAnalyze() {
    if (!fileAB || !fileBC) return;
    setError(""); setStep("loading_ab");
    try {
      const ab = await analyzeKM(fileAB, labelA, labelB);
      setResultAB(ab);
      setStep("loading_bc");
      const bc = await analyzeKM(fileBC, labelB, labelC);
      setResultBC(bc);

      const hrAbInfo = ab.logrank.hazard_ratio;
      const hrBcInfo = bc.logrank.hazard_ratio;
      setStep("loading_indirect");
      const res = await indirectComparison({
        hr_ab: hrAbInfo.value!, ci_lower_ab: hrAbInfo.ci_lower!, ci_upper_ab: hrAbInfo.ci_upper!,
        hr_bc: hrBcInfo.value!, ci_lower_bc: hrBcInfo.ci_lower!, ci_upper_bc: hrBcInfo.ci_upper!,
        label_a: labelA, label_b: labelB, label_c: labelC,
      });
      setIndirect(res); setStep("done");
    } catch (e: unknown) {
      setError((e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? String(e));
      setStep("error");
    }
  }

  async function handlePubmedAnalyze() {
    if (!hrAB || !hrBC) return;
    setError(""); setStep("loading_indirect");
    try {
      const res = await indirectComparison({
        hr_ab: +hrAB.hr, ci_lower_ab: +hrAB.lower, ci_upper_ab: +hrAB.upper,
        hr_bc: +hrBC.hr, ci_lower_bc: +hrBC.lower, ci_upper_bc: +hrBC.upper,
        label_a: labelA, label_b: labelB, label_c: labelC,
      });
      setIndirect(res); setStep("done");
    } catch (e: unknown) {
      setError(String(e)); setStep("error");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Indirect Comparison (Bucher Method)</h1>
        <p className="text-slate-500 text-sm mt-1">
          Estimate A vs C by combining A vs B and B vs C trials via a common comparator.
        </p>
      </div>

      {/* Demo card */}
      <div>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
          Try a demo (no API key required)
        </p>
        <button
          onClick={handleLoadDemo}
          className={clsx(
            "w-full text-left rounded-xl border p-4 transition-all",
            demoLoaded
              ? "border-primary bg-blue-50 ring-1 ring-primary"
              : "border-slate-200 bg-white hover:border-slate-400 hover:shadow-sm"
          )}
        >
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">OS</span>
            <span className="text-xs text-slate-400">mCRC 3rd-line · FRESCO × CORRECT</span>
          </div>
          <p className="font-semibold text-slate-800 text-sm">Fruquintinib vs Regorafenib (via Placebo)</p>
          <p className="text-xs text-slate-500 mt-0.5">
            Pre-filled with published HR values — click Run to compute indirect comparison instantly
          </p>
          <div className="mt-2 flex gap-4 text-xs text-slate-400 font-mono">
            <span>Fruq vs Placebo: 0.57 (0.45–0.73)</span>
            <span>Placebo vs Rego: 1.30 (1.06–1.56)</span>
          </div>
        </button>
      </div>

      {/* Pre-fill confirmation */}
      {demoLoaded && hrAB && hrBC && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-xs text-blue-800 space-y-1">
          <p className="font-semibold">Demo values loaded — labels and HRs pre-filled below.</p>
          <p>Click <strong>Run Indirect Comparison</strong> to compute.</p>
        </div>
      )}

      <div className="relative">
        <div className="absolute inset-0 flex items-center" aria-hidden>
          <div className="w-full border-t border-slate-200" />
        </div>
        <div className="relative flex justify-center">
          <span className="bg-slate-50 px-3 text-xs text-slate-400">or enter your own data</span>
        </div>
      </div>

      <ApiKeyBanner />

      {/* Treatment labels */}
      <div className="flex gap-3">
        {(["A", "B", "C"] as const).map((t) => {
          const setters = { A: setLabelA, B: setLabelB, C: setLabelC };
          const vals = { A: labelA, B: labelB, C: labelC };
          return (
            <div key={t} className="flex-1">
              <label className="text-xs text-slate-400 mb-1 block">Treatment {t} label</label>
              <input
                className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
                value={vals[t]}
                onChange={(e) => { setters[t](e.target.value); setDemoLoaded(false); }}
              />
            </div>
          );
        })}
      </div>

      {/* Mode tabs */}
      <div className="flex gap-2 border-b border-slate-200">
        {(["pubmed", "upload"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={clsx(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              mode === m ? "border-primary text-primary" : "border-transparent text-slate-500 hover:text-slate-800"
            )}
          >
            {m === "pubmed" ? "Search PubMed / Enter HR" : "Upload KM Images"}
          </button>
        ))}
      </div>

      {/* Upload mode */}
      {mode === "upload" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <p className="text-sm font-semibold">{labelA} vs {labelB} — KM Figure</p>
            <DropZone onFile={setFileAB} label={`Drop ${labelA} vs ${labelB} KM image`} />
            {resultAB && <KMChart curves={resultAB.logrank.km_curves} xLabel="Time" />}
          </div>
          <div className="space-y-2">
            <p className="text-sm font-semibold">{labelB} vs {labelC} — KM Figure</p>
            <DropZone onFile={setFileBC} label={`Drop ${labelB} vs ${labelC} KM image`} />
            {resultBC && <KMChart curves={resultBC.logrank.km_curves} xLabel="Time" />}
          </div>
          <button
            onClick={handleUploadAnalyze}
            disabled={!fileAB || !fileBC || loading}
            className="md:col-span-2 w-full bg-primary text-white rounded-xl py-3 font-semibold text-sm disabled:opacity-50 hover:bg-blue-700"
          >
            {step === "loading_ab" ? `Analyzing ${labelA} vs ${labelB}...`
              : step === "loading_bc" ? `Analyzing ${labelB} vs ${labelC}...`
              : step === "loading_indirect" ? "Computing indirect comparison..."
              : "Analyze & Compare"}
          </button>
        </div>
      )}

      {/* PubMed / manual HR mode */}
      {mode === "pubmed" && (
        <div className="space-y-4">
          {/* Show pre-filled HR summary if demo loaded, else show ArticleSlots */}
          {demoLoaded && hrAB && hrBC ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-sm">
                <p className="font-semibold text-slate-700 mb-1">{labelA} vs {labelB}</p>
                <p className="text-xs text-slate-500 mb-2">FRESCO trial (Li et al. JAMA 2018)</p>
                <p className="font-mono text-slate-800">HR {hrAB.hr} (95% CI {hrAB.lower}–{hrAB.upper})</p>
              </div>
              <div className="bg-slate-50 rounded-xl border border-slate-200 p-4 text-sm">
                <p className="font-semibold text-slate-700 mb-1">{labelB} vs {labelC}</p>
                <p className="text-xs text-slate-500 mb-2">CORRECT trial (Grothey et al. Lancet 2013, inverted)</p>
                <p className="font-mono text-slate-800">HR {hrBC.hr} (95% CI {hrBC.lower}–{hrBC.upper})</p>
              </div>
            </div>
          ) : (
            <>
              <p className="text-xs text-slate-500">
                Search for two trials sharing a common comparator ({labelB}).
                Select the KM figure from each article — open-access figures load automatically; others require manual upload.
              </p>
              <ArticleSlot
                label={`Article 1 — ${labelA} vs ${labelB}`}
                onHR={(hr) => setHrAB(hr)}
              />
              <ArticleSlot
                label={`Article 2 — ${labelB} vs ${labelC}`}
                onHR={(hr) => setHrBC(hr)}
              />
            </>
          )}

          <button
            onClick={handlePubmedAnalyze}
            disabled={!hrAB || !hrBC || loading}
            className="w-full bg-primary text-white rounded-xl py-3 font-semibold text-sm disabled:opacity-50 hover:bg-blue-700"
          >
            {step === "loading_indirect" ? "Computing..." : "Run Indirect Comparison"}
          </button>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Results */}
      {indirect && (
        <div className="bg-white rounded-xl border border-slate-200 p-6 space-y-5">
          <h2 className="font-semibold text-lg">Indirect Comparison Result</h2>
          <p className="text-sm text-slate-500">{indirect.comparison}</p>

          <div className={clsx(
            "rounded-xl p-5 text-center",
            indirect.result.significant ? "bg-green-50 border border-green-200" : "bg-slate-50 border border-slate-200"
          )}>
            <p className="text-3xl font-bold text-slate-800">HR = {indirect.result.hr.toFixed(2)}</p>
            <p className="text-slate-600 mt-1">
              95% CI: {indirect.result.ci_lower.toFixed(2)} – {indirect.result.ci_upper.toFixed(2)}
            </p>
            <p className={clsx("mt-2 font-semibold", indirect.result.significant ? "text-green-700" : "text-slate-600")}>
              p = {indirect.result.p_value < 0.001 ? "< 0.001" : indirect.result.p_value.toFixed(4)}
              {indirect.result.significant ? " — Significant" : " — Not significant"}
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            {Object.entries(indirect.inputs).map(([comp, info]) => (
              <div key={comp} className="bg-slate-50 rounded-lg p-3">
                <p className="font-medium text-slate-700 mb-1">{comp.replace("_vs_", " vs ")}</p>
                <p className="font-mono">HR {info.hr.toFixed(2)} ({info.ci_lower.toFixed(2)}–{info.ci_upper.toFixed(2)})</p>
              </div>
            ))}
          </div>

          <div>
            <p className="text-xs font-semibold text-slate-500 mb-2">Assumptions</p>
            <ul className="space-y-1">
              {indirect.assumptions.map((a, i) => (
                <li key={i} className="text-xs text-slate-500 flex gap-2">
                  <span className="text-amber-500">!</span>{a}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}
