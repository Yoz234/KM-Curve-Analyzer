import axios from "axios";
import { getApiKey, getProvider } from "./apiKey";

export const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const api = axios.create({ baseURL: BASE, timeout: 120000 }); // 2 min for LLM calls

// Inject API key and provider headers on every request
api.interceptors.request.use((config) => {
  const key = getApiKey();
  const provider = getProvider();
  if (key) config.headers["x-api-key"] = key;
  config.headers["x-provider"] = provider;
  return config;
});

// ---- Types ----------------------------------------------------------------

export interface CurvePoint { time: number; survival: number }
export interface AtRiskEntry { time: number; n_at_risk: number }

export interface GroupExtraction {
  name: string;
  color_description: string;
  curve_points: CurvePoint[];
  at_risk_table: AtRiskEntry[];
  censor_marks: number[];
}

export interface KMExtraction {
  groups: GroupExtraction[];
  x_axis: { label: string; min: number; max: number; unit: string };
  y_axis: { label: string; is_percentage: boolean };
  title: string;
  n_groups: number;
  extraction_notes: string;
}

export interface HazardRatio {
  value: number;
  ci_lower: number;
  ci_upper: number;
  label: string;
}

export interface LogRankResult {
  test: string;
  p_value: number;
  test_statistic: number;
  significant: boolean;
  hazard_ratio: HazardRatio;
  median_survival: Record<string, number | null>;
  km_curves: Record<string, CurvePoint[]>;
  n_patients: Record<string, number>;
  n_events: Record<string, number>;
}

export interface AnalyzeResponse {
  extraction: KMExtraction;
  groups: { name: string; n: number; n_events: number }[];
  logrank: LogRankResult;
}

export interface IndirectResult {
  method: string;
  comparison: string;
  inputs: Record<string, { hr: number; ci_lower: number; ci_upper: number; se_log_hr: number }>;
  result: {
    hr: number;
    ci_lower: number;
    ci_upper: number;
    z_statistic: number;
    p_value: number;
    significant: boolean;
    label: string;
  };
  assumptions: string[];
}

// ---- Calls ----------------------------------------------------------------

export async function analyzeKM(
  file: File,
  groupAName?: string,
  groupBName?: string,
): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.append("file", file);
  if (groupAName) fd.append("group_a_name", groupAName);
  if (groupBName) fd.append("group_b_name", groupBName);
  const { data } = await api.post<AnalyzeResponse>("/api/analyze-km", fd);
  return data;
}

export async function extractKM(file: File) {
  const fd = new FormData();
  fd.append("file", file);
  const { data } = await api.post("/api/extract-km", fd);
  return data;
}

export async function indirectComparison(payload: {
  hr_ab: number; ci_lower_ab: number; ci_upper_ab: number;
  hr_bc: number; ci_lower_bc: number; ci_upper_bc: number;
  label_a: string; label_b: string; label_c: string;
}): Promise<IndirectResult> {
  const { data } = await api.post<IndirectResult>("/api/indirect-comparison", payload);
  return data;
}

export interface PubmedArticle {
  pmid: string;
  title: string;
  year: string;
  authors: string[];
  journal: string;
  abstract: string;
}

export async function searchPubmed(query: string, maxResults = 8): Promise<PubmedArticle[]> {
  const { data } = await api.get<{ results: PubmedArticle[] }>("/api/search-pubmed", {
    params: { q: query, max_results: maxResults },
  });
  return data.results;
}

export interface PmcFigure {
  fig_id: string;
  label: string;
  caption: string;
  url: string;
  pmcid: string;
}

export async function getPmcFigures(pmid: string): Promise<{ pmcid: string | null; figures: PmcFigure[] }> {
  const { data } = await api.get("/api/pmc-figures", { params: { pmid } });
  return data;
}

export async function extractKMFromUrl(figureUrl: string): Promise<{ extraction: KMExtraction; warnings: Record<string, string[]> }> {
  const fd = new FormData();
  fd.append("figure_url", figureUrl);
  const { data } = await api.post("/api/extract-km-from-url", fd);
  return data;
}

export async function analyzeFromExtraction(
  extraction: KMExtraction,
  groupAIndex: number,
  groupBIndex: number,
): Promise<AnalyzeResponse> {
  const { data } = await api.post<AnalyzeResponse>("/api/analyze-from-extraction", {
    extraction,
    group_a_index: groupAIndex,
    group_b_index: groupBIndex,
  });
  return data;
}

export async function analyzeKMFromUrl(
  figureUrl: string,
  groupAName?: string,
  groupBName?: string,
): Promise<AnalyzeResponse> {
  const fd = new FormData();
  fd.append("figure_url", figureUrl);
  if (groupAName) fd.append("group_a_name", groupAName);
  if (groupBName) fd.append("group_b_name", groupBName);
  const { data } = await api.post<AnalyzeResponse>("/api/analyze-km-from-url", fd);
  return data;
}

export async function extractHR(text: string) {
  const fd = new FormData();
  fd.append("text", text);
  const { data } = await api.post("/api/extract-hr", fd);
  return data;
}
