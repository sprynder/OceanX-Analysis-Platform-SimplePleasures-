"use client";

import { useState } from "react";
import { SearchROIResult, SearchResponse } from "@/types";
import { toMediaUrl } from "@/utils/media";

type Props = {
  /** Per-video search when provided; cross-video when omitted */
  videoId?: string;
  apiBase: string;
  onResultsChange?: (resultIds: Set<string>) => void;
};

const DEFAULTS = { dedupEnabled: true, tauTime: 2.0, tauIou: 0.3, tauEmb: 0.85, topK: 10 };

export function SearchBar({ videoId, apiBase, onResultsChange }: Props) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchROIResult[]>([]);
  const [rawCount, setRawCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showDedup, setShowDedup] = useState(false);

  // Dedup controls
  const [dedupEnabled, setDedupEnabled] = useState(DEFAULTS.dedupEnabled);
  const [tauTime, setTauTime] = useState(DEFAULTS.tauTime);
  const [tauIou, setTauIou] = useState(DEFAULTS.tauIou);
  const [tauEmb, setTauEmb] = useState(DEFAULTS.tauEmb);

  const endpoint = videoId
    ? `${apiBase}/videos/${videoId}/search`
    : `${apiBase}/global/search`;

  const handleSearch = async () => {
    const trimmed = query.trim();
    if (!trimmed) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setRawCount(null);
    onResultsChange?.(new Set());

    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: trimmed,
          dedup_enabled: dedupEnabled,
          tau_time: tauTime,
          tau_iou: tauIou,
          tau_emb: tauEmb,
        }),
      });

      if (!res.ok) throw new Error(`Search failed (${res.status})`);

      const data: SearchResponse = await res.json();
      setResults(data.results);
      setRawCount(data.raw_count);
      onResultsChange?.(new Set(data.results.map((r) => r.roi_id)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setQuery("");
    setResults([]);
    setRawCount(null);
    setError(null);
    onResultsChange?.(new Set());
  };

  const dedupSuppressed =
    rawCount !== null && dedupEnabled ? rawCount - results.length : 0;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Semantic Search</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {videoId
              ? "BioCLIP text-to-image search within this video."
              : "Cross-video search across the entire Qdrant database."}
          </p>
        </div>
        <button
          onClick={() => setShowDedup((v) => !v)}
          className={`shrink-0 rounded-lg border px-3 py-1.5 text-xs font-medium transition ${
            showDedup
              ? "border-slate-900 bg-slate-900 text-white"
              : "border-slate-200 text-slate-500 hover:bg-slate-50"
          }`}
        >
          ⚙ Dedup
        </button>
      </div>

      {/* Dedup controls panel */}
      {showDedup && (
        <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Deduplication settings
            </span>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input
                type="checkbox"
                checked={dedupEnabled}
                onChange={(e) => setDedupEnabled(e.target.checked)}
                className="rounded"
              />
              Enabled
            </label>
          </div>

          {dedupEnabled && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Δt window (s)", value: tauTime, set: setTauTime, min: 0, max: 10, step: 0.5 },
                { label: "IoU threshold", value: tauIou, set: setTauIou, min: 0, max: 1, step: 0.05 },
                { label: "Emb similarity", value: tauEmb, set: setTauEmb, min: 0, max: 1, step: 0.05 },
              ].map(({ label, value, set, min, max, step }) => (
                <div key={label} className="flex flex-col gap-1">
                  <div className="flex justify-between">
                    <span className="text-[11px] text-slate-500">{label}</span>
                    <span className="text-[11px] font-semibold text-slate-700">{value.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={min}
                    max={max}
                    step={step}
                    value={value}
                    onChange={(e) => set(parseFloat(e.target.value))}
                    className="w-full accent-slate-800"
                  />
                </div>
              ))}
            </div>
          )}

          <p className="text-[11px] text-slate-400">
            All three gates must fire to suppress a result: Δt &lt; τ_time AND IoU &gt; τ_iou AND cosine_sim &gt; τ_emb
          </p>
        </div>
      )}

      <div className="mt-4 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="e.g. bat ray, stingray near sand"
          className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
        {results.length > 0 && (
          <button
            onClick={handleClear}
            className="rounded-lg border border-slate-200 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50"
          >
            Clear
          </button>
        )}
      </div>

      {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}

      {results.length > 0 && (
        <div className="mt-6">
          <div className="mb-3 flex items-center gap-2 flex-wrap">
            <span className="text-sm text-slate-500">
              {results.length} result{results.length !== 1 ? "s" : ""}
            </span>
            {rawCount !== null && dedupEnabled && dedupSuppressed > 0 && (
              <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-700">
                {dedupSuppressed} duplicate{dedupSuppressed !== 1 ? "s" : ""} removed by dedup
              </span>
            )}
            {rawCount !== null && !dedupEnabled && (
              <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
                dedup off — showing all {rawCount} raw candidates
              </span>
            )}
            {videoId && (
              <span className="text-xs text-slate-400">— highlighted in scatter below</span>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {results.map((r) => (
              <div key={r.roi_id} className="flex flex-col gap-1.5">
                <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={toMediaUrl(r.roi_url)}
                    alt={`ROI at ${r.timestamp_sec.toFixed(1)}s`}
                    className="w-full object-contain"
                  />
                </div>
                <div className="flex items-center gap-1 flex-wrap">
                  <span className="inline-flex items-center rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600 whitespace-nowrap">
                    t&nbsp;=&nbsp;{r.timestamp_sec.toFixed(1)}s
                  </span>
                  <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700 whitespace-nowrap">
                    ★&nbsp;{r.score.toFixed(3)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && !error && (
        <p className="mt-4 text-sm text-slate-500">No results found.</p>
      )}
    </div>
  );
}
