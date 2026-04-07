"use client";

// Must be loaded via dynamic(() => import(...), { ssr: false }) — Plotly needs browser APIs.

import { useState, useMemo, useRef, useCallback } from "react";
import Plot from "react-plotly.js";
import { GlobalRoi, GlobalUMAPResponse } from "@/types";
import { SearchBar } from "@/components/SearchBar";
import { toMediaUrl } from "@/utils/media";

type Props = { apiBase: string };

function clusterColor(clusterId: number): string {
  if (clusterId === -1) return "rgba(150,150,150,0.25)";
  return `hsl(${(clusterId * 47) % 360}, 65%, 55%)`;
}

function clusterColorSolid(clusterId: number): string {
  if (clusterId === -1) return "rgb(150,150,150)";
  return `hsl(${(clusterId * 47) % 360}, 65%, 55%)`;
}

const DEDUP_DEFAULTS = { tauTime: 2.0, tauIou: 0.3, tauEmb: 0.85 };

const DEDUP_EXPLANATIONS = [
  {
    label: "Δt window (s) — τ_time",
    description:
      "Suppresses an ROI if it occurred within this many seconds of an earlier, more similar ROI in the same video. " +
      "Low (~1 s): only removes near-duplicate frames. High (~5 s): collapses entire sightings of the same animal into one.",
  },
  {
    label: "IoU threshold — τ_iou",
    description:
      "Intersection-over-Union between bounding boxes. Only suppresses if boxes substantially overlap. " +
      "Low (~0.1): any nearby crop is suppressed. High (~0.6): only near-identical crops are removed.",
  },
  {
    label: "Embedding similarity — τ_emb",
    description:
      "BioCLIP cosine similarity. Only suppresses if the two ROIs look visually identical. " +
      "Low (~0.7): similar-looking animals deduplicated. High (~0.95): only exact-same-frame duplicates removed.",
  },
];

export default function GlobalView({ apiBase }: Props) {
  const [data, setData] = useState<GlobalUMAPResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRoi, setHoveredRoi] = useState<GlobalRoi | null>(null);
  const [searchHighlightIds, setSearchHighlightIds] = useState<Set<string>>(new Set());

  // Dedup controls
  const [dedupEnabled, setDedupEnabled] = useState(false);
  const [showDedup, setShowDedup] = useState(false);
  const [showDedupHelp, setShowDedupHelp] = useState(false);
  const [tauTime, setTauTime] = useState(DEDUP_DEFAULTS.tauTime);
  const [tauIou, setTauIou] = useState(DEDUP_DEFAULTS.tauIou);
  const [tauEmb, setTauEmb] = useState(DEDUP_DEFAULTS.tauEmb);

  const loadGlobal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/global/umap`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dedup_enabled: dedupEnabled,
          tau_time: tauTime,
          tau_iou: tauIou,
          tau_emb: tauEmb,
        }),
      });
      if (!res.ok) throw new Error(`Global UMAP failed (${res.status})`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setLoading(false);
    }
  };

  // Group by global HDBSCAN cluster
  const byCluster = useMemo(() => {
    if (!data) return new Map<number, GlobalRoi[]>();
    const map = new Map<number, GlobalRoi[]>();
    for (const roi of data.rois) {
      if (!map.has(roi.cluster)) map.set(roi.cluster, []);
      map.get(roi.cluster)!.push(roi);
    }
    return map;
  }, [data]);

  const clusterIds = useMemo(
    () =>
      [...byCluster.keys()].sort((a, b) => {
        if (a === -1) return 1;
        if (b === -1) return -1;
        return a - b;
      }),
    [byCluster]
  );

  // Fixed axis ranges — computed once from data so legend-click never re-scales
  const axisRanges = useMemo(() => {
    if (!data || data.rois.length === 0) return null;
    const pad = (vals: number[]) => {
      const mn = Math.min(...vals), mx = Math.max(...vals);
      const m = (mx - mn) * 0.08;
      return [mn - m, mx + m] as [number, number];
    };
    return {
      x: pad(data.rois.map((r) => r.umap_x)),
      y: pad(data.rois.map((r) => r.umap_y)),
      z: pad(data.rois.map((r) => r.umap_z)),
    };
  }, [data]);

  const roiMap = useMemo(() => {
    if (!data) return new Map<string, GlobalRoi>();
    return new Map(data.rois.map((r) => [r.roi_id, r]));
  }, [data]);

  const traces = useMemo(() => {
    const clusterTraces = clusterIds.map((clusterId) => {
      const rois = byCluster.get(clusterId)!;
      return {
        type: "scatter3d" as const,
        mode: "markers" as const,
        name: clusterId === -1 ? "Noise" : `Cluster ${clusterId}`,
        x: rois.map((r) => r.umap_x),
        y: rois.map((r) => r.umap_y),
        z: rois.map((r) => r.umap_z),
        customdata: rois.map((r) => r.roi_id),
        hovertemplate: "<extra></extra>",
        marker: {
          color: clusterColor(clusterId),
          size: clusterId === -1 ? 5 : 8,
          opacity: clusterId === -1 ? 0.4 : 0.85,
          line: clusterId === -1 ? { width: 0 } : { width: 0.5, color: "rgba(255,255,255,0.4)" },
        },
      };
    });

    if (searchHighlightIds.size === 0) return clusterTraces;
    const matchedRois = data!.rois.filter((r) => searchHighlightIds.has(r.roi_id));
    if (matchedRois.length === 0) return clusterTraces;

    return [
      ...clusterTraces,
      {
        type: "scatter3d" as const,
        mode: "markers" as const,
        name: "Search results",
        x: matchedRois.map((r) => r.umap_x),
        y: matchedRois.map((r) => r.umap_y),
        z: matchedRois.map((r) => r.umap_z),
        customdata: matchedRois.map((r) => r.roi_id),
        hovertemplate: "<extra></extra>",
        marker: { color: "#f59e0b", size: 9, opacity: 1, symbol: "diamond",
                  line: { width: 1.5, color: "#ffffff" } },
      },
    ];
  }, [byCluster, clusterIds, searchHighlightIds, data]);

  // ─── Hover via direct DOM attachment (same pattern as EmbeddingScatterPlot) ──
  const curveIdArraysRef = useRef<string[][]>([]);
  const roiMapRef = useRef<Map<string, GlobalRoi>>(new Map());
  curveIdArraysRef.current = traces.map((t) => t.customdata as string[]);
  roiMapRef.current = roiMap;

  const handlePlotHover = useCallback((data: { points: { curveNumber?: number; pointNumber?: number; pointIndex?: number }[] }) => {
    const pt = data.points[0];
    if (!pt) return;
    const curveNumber = pt.curveNumber ?? 0;
    const pointNumber = pt.pointNumber ?? pt.pointIndex ?? 0;
    const roiId = curveIdArraysRef.current[curveNumber]?.[pointNumber];
    if (roiId) {
      const roi = roiMapRef.current.get(roiId);
      if (roi) setHoveredRoi(roi);
    }
  }, []);

  const handlePlotUnhover = useCallback(() => setHoveredRoi(null), []);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleInitialized = useCallback((_figure: any, graphDiv: any) => {
    graphDiv.on("plotly_hover", handlePlotHover);
    graphDiv.on("plotly_unhover", handlePlotUnhover);
  }, [handlePlotHover, handlePlotUnhover]);
  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Global Embedding Space</h2>
          <p className="mt-0.5 text-sm text-slate-500">
            All vectors across every video in Qdrant — coloured by HDBSCAN cluster across the full corpus.
          </p>
        </div>
        <div className="flex gap-2 shrink-0">
          <button
            onClick={() => setShowDedup((v) => !v)}
            className={`rounded-lg border px-3 py-2 text-xs font-medium transition ${
              showDedup ? "border-slate-900 bg-slate-900 text-white" : "border-slate-200 text-slate-500 hover:bg-slate-50"
            }`}
          >
            ⚙ Dedup
          </button>
          <button
            onClick={loadGlobal}
            disabled={loading}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {loading ? "Computing…" : data ? "Recompute" : "Load global view"}
          </button>
        </div>
      </div>

      {showDedup && (
        <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
              Deduplication (applied before UMAP)
            </span>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer">
              <input type="checkbox" checked={dedupEnabled}
                onChange={(e) => setDedupEnabled(e.target.checked)} className="rounded" />
              Enabled
            </label>
          </div>
          {dedupEnabled && (
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Δt window (s)", value: tauTime, set: setTauTime, min: 0, max: 10, step: 0.5 },
                { label: "IoU threshold", value: tauIou,  set: setTauIou,  min: 0, max: 1,  step: 0.05 },
                { label: "Emb similarity", value: tauEmb, set: setTauEmb,  min: 0, max: 1,  step: 0.05 },
              ].map(({ label, value, set, min, max, step }) => (
                <div key={label} className="flex flex-col gap-1">
                  <div className="flex justify-between">
                    <span className="text-[11px] text-slate-500">{label}</span>
                    <span className="text-[11px] font-semibold text-slate-700">{value.toFixed(2)}</span>
                  </div>
                  <input type="range" min={min} max={max} step={step} value={value}
                    onChange={(e) => set(parseFloat(e.target.value))}
                    className="w-full accent-slate-800" />
                </div>
              ))}
            </div>
          )}
          <p className="text-[11px] text-slate-400">
            Dedup runs per-video before UMAP — removes near-duplicate frames of the same animal.
            Hit Recompute to apply.
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

      {error && <p className="text-sm text-rose-600">{error}</p>}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span className="animate-spin">⟳</span>
          Running UMAP on all embeddings — this takes 10–30s…
        </div>
      )}

      {data && (
        <>
          <p className="text-xs text-slate-400">
            {data.roi_count} ROIs · {data.video_count} video{data.video_count !== 1 ? "s" : ""} ·{" "}
            {clusterIds.filter((id) => id !== -1).length} global clusters.
            Hover a point to preview.
            {searchHighlightIds.size > 0 && (
              <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700">
                ◆ {searchHighlightIds.size} match{searchHighlightIds.size !== 1 ? "es" : ""} highlighted
              </span>
            )}
          </p>

          <div className="flex gap-4 min-w-0 overflow-hidden">
            <div className="flex-1 min-w-0 overflow-hidden">
              <Plot
                data={traces as unknown as import("plotly.js").Data[]}
                layout={{
                  autosize: true,
                  height: 520,
                  uirevision: "static",
                  hovermode: "closest",
                  margin: { l: 0, r: 0, t: 10, b: 0 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  scene: {
                    aspectmode: "cube",
                    xaxis: { title: { text: "UMAP-1" }, showgrid: true, gridcolor: "#e2e8f0", range: axisRanges?.x },
                    yaxis: { title: { text: "UMAP-2" }, showgrid: true, gridcolor: "#e2e8f0", range: axisRanges?.y },
                    zaxis: { title: { text: "UMAP-3" }, showgrid: true, gridcolor: "#e2e8f0", range: axisRanges?.z },
                    bgcolor: "#f8fafc",
                  },
                  legend: { x: 0.01, y: 0.99, bgcolor: "rgba(255,255,255,0.85)",
                            bordercolor: "#e2e8f0", borderwidth: 1, font: { size: 11 } },
                }}
                onInitialized={handleInitialized}
                config={{ responsive: true, displayModeBar: false }}
                style={{ width: "100%" }}
                useResizeHandler
              />
            </div>

            <div className="w-52 shrink-0">
              {hoveredRoi ? (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 space-y-2">
                  <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={toMediaUrl(hoveredRoi.roi_url)} alt="ROI preview"
                         className="w-full object-contain max-h-40" />
                  </div>
                  <div className="space-y-1">
                    <p>
                      <span className="font-medium">Cluster:</span>{" "}
                      <span className="rounded px-1 py-0.5 text-[10px] text-white"
                        style={{ background: clusterColorSolid(hoveredRoi.cluster) }}>
                        {hoveredRoi.cluster === -1 ? "noise" : hoveredRoi.cluster}
                      </span>
                    </p>
                    <p><span className="font-medium">Video:</span>{" "}
                      <span className="font-mono text-[10px]" title={hoveredRoi.video_id}>
                        {hoveredRoi.video_id.slice(0, 12)}…
                      </span>
                    </p>
                    <p><span className="font-medium">Frame:</span> {hoveredRoi.frame_idx}</p>
                  </div>
                </div>
              ) : (
                <div className="flex h-full min-h-36 items-center justify-center rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
                  hover a point
                </div>
              )}
            </div>
          </div>

          <SearchBar apiBase={apiBase} onResultsChange={setSearchHighlightIds} />
        </>
      )}
    </div>
  );
}
