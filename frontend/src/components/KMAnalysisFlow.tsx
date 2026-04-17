"use client";

/**
 * KMAnalysisFlow
 *
 * Two-step KM analysis:
 *   1. Extract via LLM → get all group names
 *   2a. Exactly 2 groups → show GroupSelector (always shown now)
 *   2b. User picks any two → analyze
 *
 * Source variants:
 *   { file }       — upload: calls /api/extract-km (LLM, needs API key)
 *   { url }        — PMC URL: calls /api/extract-km-from-url (LLM, needs API key)
 *   { extraction } — demo / preloaded: skips LLM, goes straight to group selection
 */

import { useEffect, useState } from "react";
import {
  extractKM, extractKMFromUrl, analyzeFromExtraction,
  type AnalyzeResponse, type KMExtraction,
} from "@/lib/api";
import GroupSelector from "@/components/GroupSelector";

export type Source =
  | { file: File }
  | { url: string }
  | { extraction: KMExtraction; label: string }
  | null;

type FlowState = "idle" | "extracting" | "selecting" | "analyzing";

interface Props {
  source: Source;
  onResult: (result: AnalyzeResponse) => void;
  onError: (msg: string) => void;
  onLoadingChange: (loading: boolean) => void;
}

export default function KMAnalysisFlow({ source, onResult, onError, onLoadingChange }: Props) {
  const [flowState, setFlowState] = useState<FlowState>("idle");
  const [extraction, setExtraction] = useState<KMExtraction | null>(null);
  const [statusMsg, setStatusMsg] = useState("");

  useEffect(() => {
    if (!source) { setFlowState("idle"); setExtraction(null); return; }

    if ("extraction" in source) {
      // Demo / preloaded path — skip LLM entirely
      setExtraction(source.extraction);
      setFlowState("selecting");
      setStatusMsg("");
      return;
    }

    void runExtract(source);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source]);

  async function runExtract(src: { file: File } | { url: string }) {
    setFlowState("extracting");
    onLoadingChange(true);
    setStatusMsg("Extracting groups from figure... (LLM, 20–40 s)");
    setExtraction(null);

    try {
      let ext: KMExtraction;
      if ("file" in src) {
        const res = await extractKM(src.file);
        ext = res.extraction as KMExtraction;
      } else {
        const res = await extractKMFromUrl(src.url);
        ext = res.extraction as KMExtraction;
      }

      const nGroups = ext.groups?.length ?? 0;
      if (nGroups < 2) throw new Error(`Only ${nGroups} group(s) detected — need at least 2.`);

      setExtraction(ext);
      setFlowState("selecting");
      onLoadingChange(false);
      setStatusMsg("");
    } catch (e: unknown) {
      onError(errorMsg(e));
      setFlowState("idle");
      onLoadingChange(false);
      setStatusMsg("");
    }
  }

  async function runAnalyze(ext: KMExtraction, idxA: number, idxB: number) {
    setFlowState("analyzing");
    onLoadingChange(true);
    setStatusMsg("Computing log-rank statistics...");

    try {
      const result = await analyzeFromExtraction(ext, idxA, idxB);
      setFlowState("selecting");   // stay in selecting so user can re-pick groups
      setStatusMsg("");
      onLoadingChange(false);
      onResult(result);
    } catch (e: unknown) {
      onError(errorMsg(e));
      setFlowState(extraction ? "selecting" : "idle");
      onLoadingChange(false);
      setStatusMsg("");
    }
  }

  function errorMsg(e: unknown): string {
    return (
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as { message?: string })?.message ??
      String(e)
    );
  }

  if (flowState === "idle") return null;

  if (flowState === "extracting" || flowState === "analyzing") {
    return <p className="text-sm text-slate-500 text-center animate-pulse">{statusMsg}</p>;
  }

  if (flowState === "selecting" && extraction) {
    return (
      <GroupSelector
        groups={extraction.groups.map((g) => g.name)}
        onConfirm={(idxA, idxB) => runAnalyze(extraction, idxA, idxB)}
      />
    );
  }

  return null;
}
