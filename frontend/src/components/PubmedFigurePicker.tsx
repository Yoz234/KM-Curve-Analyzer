"use client";

import { useState } from "react";
import { BASE, searchPubmed, getPmcFigures, type PubmedArticle, type PmcFigure } from "@/lib/api";
import DropZone from "@/components/DropZone";
import clsx from "clsx";

interface Props {
  /** Called when a PMC figure URL is selected */
  onUrl: (url: string) => void;
  /** Called when user uploads a file manually */
  onFile: (file: File) => void;
  /** Optional label shown at top */
  label?: string;
  /** Whether analysis is in progress (disables clicks) */
  analyzing?: boolean;
}

/**
 * Reusable PubMed search → article select → PMC figure pick (or manual upload).
 * Does NOT perform analysis itself; delegates via onUrl / onFile.
 */
export default function PubmedFigurePicker({ onUrl, onFile, label, analyzing }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<PubmedArticle[]>([]);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState("");

  const [selected, setSelected] = useState<PubmedArticle | null>(null);
  const [figures, setFigures] = useState<PmcFigure[]>([]);
  const [pmcid, setPmcid] = useState<string | null | undefined>(undefined); // undefined = not fetched yet
  const [loadingFigs, setLoadingFigs] = useState(false);
  const [selectedFig, setSelectedFig] = useState<PmcFigure | null>(null);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true); setSearchError(""); setResults([]);
    try {
      const res = await searchPubmed(query.trim());
      setResults(res);
      if (res.length === 0) setSearchError("No results found.");
    } catch {
      setSearchError("Search failed. Check backend connection.");
    } finally {
      setSearching(false);
    }
  }

  async function handleSelect(a: PubmedArticle) {
    setSelected(a); setResults([]); setFigures([]);
    setPmcid(undefined); setSelectedFig(null);
    setLoadingFigs(true);
    try {
      const res = await getPmcFigures(a.pmid);
      setPmcid(res.pmcid);
      setFigures(res.figures);
    } catch {
      setPmcid(null); setFigures([]);
    } finally {
      setLoadingFigs(false);
    }
  }

  function handleDeselect() {
    setSelected(null); setResults([]); setFigures([]);
    setPmcid(undefined); setSelectedFig(null);
  }

  function handleFigureClick(fig: PmcFigure) {
    if (analyzing) return;
    setSelectedFig(fig);
    onUrl(fig.url);
  }

  const noFigAccess = !loadingFigs && pmcid !== undefined && (pmcid === null || figures.length === 0);

  return (
    <div className="space-y-3">
      {label && <p className="text-sm font-semibold text-slate-700">{label}</p>}

      {/* Search box */}
      {!selected && (
        <>
          <div className="flex gap-2">
            <input
              className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm"
              placeholder='e.g. pembrolizumab NSCLC "overall survival"'
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            />
            <button
              onClick={handleSearch}
              disabled={searching || !query.trim()}
              className="px-4 py-2 bg-slate-700 text-white text-sm rounded-lg hover:bg-slate-800 disabled:opacity-50"
            >
              {searching ? "..." : "Search"}
            </button>
          </div>

          {searchError && <p className="text-xs text-red-500">{searchError}</p>}

          {results.length > 0 && (
            <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 max-h-60 overflow-y-auto">
              {results.map((a) => (
                <div
                  key={a.pmid}
                  className="p-3 hover:bg-slate-50 cursor-pointer"
                  onClick={() => handleSelect(a)}
                >
                  <p className="text-sm font-medium text-slate-800 line-clamp-2">{a.title}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {a.authors.join(", ")} · {a.journal} · {a.year}
                  </p>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* Selected article */}
      {selected && (
        <div className="space-y-3">
          <div className="flex justify-between items-start gap-2 bg-blue-50 rounded-lg p-3">
            <div>
              <p className="text-sm font-medium text-blue-900 line-clamp-2">{selected.title}</p>
              <p className="text-xs text-blue-700 mt-0.5">
                {selected.authors.join(", ")} · {selected.year}
              </p>
              {pmcid && figures.length > 0 && (
                <p className="text-xs text-green-700 mt-0.5">{pmcid} — open access figures available</p>
              )}
              {pmcid && !loadingFigs && figures.length === 0 && (
                <p className="text-xs text-amber-600 mt-0.5">{pmcid} — figures hosted by publisher</p>
              )}
              {!loadingFigs && pmcid === null && (
                <p className="text-xs text-amber-600 mt-0.5">Full text not in PMC (may require journal subscription)</p>
              )}
            </div>
            <button
              onClick={handleDeselect}
              className="text-xs text-blue-500 hover:text-blue-700 whitespace-nowrap"
            >
              Change
            </button>
          </div>

          {loadingFigs && <p className="text-xs text-slate-500">Fetching PMC figures...</p>}

          {/* PMC figures grid */}
          {figures.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 mb-2">Select the KM figure:</p>
              <div className="grid grid-cols-2 gap-2 max-h-72 overflow-y-auto">
                {figures.map((fig) => (
                  <div
                    key={fig.fig_id}
                    onClick={() => handleFigureClick(fig)}
                    className={clsx(
                      "border rounded-lg p-2 cursor-pointer hover:border-blue-400 transition-colors",
                      selectedFig?.fig_id === fig.fig_id
                        ? "border-blue-500 bg-blue-50"
                        : "border-slate-200",
                      analyzing && "opacity-50 cursor-not-allowed"
                    )}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={`${BASE}/api/proxy-image?url=${encodeURIComponent(fig.url)}`}
                      alt={fig.label}
                      className="w-full h-24 object-contain bg-white rounded"
                    />
                    <p className="text-xs font-medium text-slate-700 mt-1">{fig.label}</p>
                    <p className="text-xs text-slate-500 line-clamp-2">{fig.caption}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Fallback: manual upload */}
          {noFigAccess && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 space-y-2">
              <p className="text-xs text-amber-800 font-medium">
                {pmcid === null
                  ? "This article is not available in PMC Open Access. Please obtain the KM figure from the journal website."
                  : "Figures for this article are hosted by the publisher and cannot be fetched automatically. Please download the KM figure from the journal website."}
              </p>
              <p className="text-xs text-amber-700">Upload the KM figure below to proceed:</p>
              <DropZone onFile={onFile} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
