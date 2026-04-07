"use client";

import { useRef, useState } from "react";
import { SearchROIResult, SearchResponse } from "@/types";
import { toMediaUrl } from "@/utils/media";

type Props = {
  /** Per-video search when provided; cross-video when omitted */
  videoId?: string;
  apiBase: string;
  onResultsChange?: (resultIds: Set<string>) => void;
};

const DEFAULTS = { dedupEnabled: true, tauTime: 2.0, tauIou: 0.3, tauEmb: 0.85, topK: 10 };

const DEDUP_EXPLANATIONS = [
  {
    label: "Δt window (s) — τ_time",
    description:
      "Suppresses a result if it occurred within this many seconds of an earlier, more similar result in the same video. " +
      "Low (~1 s): only removes near-duplicate frames. High (~5 s): collapses entire sightings of the same animal into one result.",
  },
  {
    label: "IoU threshold — τ_iou",
    description:
      "Intersection-over-Union between bounding boxes. Suppresses a result only if the boxes substantially overlap. " +
      "Low (~0.1): any nearby box is suppressed. High (~0.6): only near-identical crops are suppressed.",
  },
  {
    label: "Embedding similarity — τ_emb",
    description:
      "BioCLIP cosine similarity between two ROI embeddings. Suppresses a result only if it looks visually identical. " +
      "Low (~0.7): similar-looking animals deduplicated. High (~0.95): only exact-same-frame duplicates removed.",
  },
];

export function SearchBar({ videoId, apiBase, onResultsChange }: Props) {
  const [mode, setMode] = useState<"text" | "image">("text");
  const [query, setQuery] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [results, setResults] = useState<SearchROIResult[]>([]);
  const [rawCount, setRawCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showDedup, setShowDedup] = useState(false);
  const [showDedupHelp, setShowDedupHelp] = useState(false);

  const [dedupEnabled, setDedupEnabled] = useState(DEFAULTS.dedupEnabled);
  const [tauTime, setTauTime] = useState(DEFAULTS.tauTime);
  const [tauIou, setTauIou] = useState(DEFAULTS.tauIou);
  const [tauEmb, setTauEmb] = useState(DEFAULTS.tauEmb);

  const textEndpoint = videoId
    ? `${apiBase}/videos/${videoId}/search`
    : `${apiBase}/global/search`;

  const imageEndpoint = videoId
    ? `${apiBase}/videos/${videoId}/search-by-image`
    : `${apiBase}/global/search-by-image`;

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    setImageFile(file);
    if (file) {
      const url = URL.createObjectURL(file);
      setImagePreview(url);
    } else {
      setImagePreview(null);
    }
  };

  const handleSearch = async () => {
    if (mode === "text" && !query.trim()) return;
    if (mode === "image" && !imageFile) return;

    setLoading(true);
    setError(null);
    setResults([]);
    setRawCount(null);
    onResultsChange?.(new Set());

    try {
      let res: Response;

      if (mode === "text") {
        res = await fetch(textEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query: query.trim(),
            dedup_enabled: dedupEnabled,
            tau_time: tauTime,
            tau_iou: tauIou,
            tau_emb: tauEmb,
          }),
        });
      } else {
        // Convert image file to base64
        const b64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => {
            const result = reader.result as string;
            // Strip data URL prefix (e.g. "data:image/jpeg;base64,")
            resolve(result.split(",")[1]);
          };
          reader.onerror = reject;
          reader.readAsDataURL(imageFile!);
        });

        res = await fetch(imageEndpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            image_b64: b64,
            dedup_enabled: dedupEnabled,
            tau_time: tauTime,
            tau_iou: tauIou,
            tau_emb: tauEmb,
          }),
        });
      }

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
    setImageFile(null);
    setImagePreview(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
    setResults([]);
    setRawCount(null);
    setError(null);
    onResultsChange?.(new Set());
  };

  const dedupSuppressed =
    rawCount !== null && dedupEnabled ? rawCount - results.length : 0;

  const canSearch = mode === "text" ? query.trim().length > 0 : imageFile !== null;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Semantic Search</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            {videoId
              ? "BioCLIP search within this video."
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

          {/* Collapsible explanation */}
          <button
            onClick={() => setShowDedupHelp((v) => !v)}
            className="flex items-center gap-1 text-[11px] font-medium text-slate-500 hover:text-slate-700 transition"
          >
            {showDedupHelp ? "▲" : "▼"} What do these parameters do?
          </button>
          {showDedupHelp && (
            <div className="space-y-2 border-t border-slate-200 pt-2">
              {DEDUP_EXPLANATIONS.map(({ label, description }) => (
                <div key={label}>
                  <p className="text-[11px] font-semibold text-slate-600">{label}</p>
                  <p className="text-[11px] text-slate-500 leading-relaxed">{description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Mode toggle */}
      <div className="mt-4 flex gap-1 rounded-lg border border-slate-200 p-1 w-fit">
        <button
          onClick={() => setMode("text")}
          className={`rounded px-3 py-1 text-xs font-medium transition ${
            mode === "text" ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50"
          }`}
        >
          Text
        </button>
        <button
          onClick={() => setMode("image")}
          className={`rounded px-3 py-1 text-xs font-medium transition ${
            mode === "image" ? "bg-slate-900 text-white" : "text-slate-500 hover:bg-slate-50"
          }`}
        >
          Image
        </button>
      </div>

      {/* Input area */}
      <div className="mt-3 flex gap-2 items-start">
        {mode === "text" ? (
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="e.g. bat ray, stingray near sand"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
        ) : (
          <div className="flex-1 flex items-center gap-3">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition"
            >
              {imageFile ? "Change image" : "Choose image…"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageChange}
              className="hidden"
            />
            {imagePreview && (
              <img
                src={imagePreview}
                alt="Query preview"
                className="h-10 w-10 rounded object-cover border border-slate-200"
              />
            )}
            {imageFile && (
              <span className="text-xs text-slate-500 truncate max-w-[160px]">{imageFile.name}</span>
            )}
          </div>
        )}

        <button
          onClick={handleSearch}
          disabled={loading || !canSearch}
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
              <span className="text-xs text-slate-400">— highlighted in scatter above</span>
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

      {!loading && results.length === 0 && (mode === "text" ? query : imageFile) && !error && (
        <p className="mt-4 text-sm text-slate-500">No results found.</p>
      )}
    </div>
  );
}
