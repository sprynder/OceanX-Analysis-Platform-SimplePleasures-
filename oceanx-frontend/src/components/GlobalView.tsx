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

export default function GlobalView({ apiBase }: Props) {
  const [data, setData] = useState<GlobalUMAPResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hoveredRoi, setHoveredRoi] = useState<GlobalRoi | null>(null);
  const [searchHighlightIds, setSearchHighlightIds] = useState<Set<string>>(new Set());

  const loadGlobal = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${apiBase}/global/umap`, { method: "POST" });
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
        <button
          onClick={loadGlobal}
          disabled={loading}
          className="shrink-0 rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {loading ? "Computing…" : data ? "Recompute" : "Load global view"}
        </button>
      </div>

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
                  hovermode: "closest",
                  margin: { l: 0, r: 0, t: 10, b: 0 },
                  paper_bgcolor: "rgba(0,0,0,0)",
                  scene: {
                    xaxis: { title: { text: "UMAP-1" }, showgrid: true, gridcolor: "#e2e8f0" },
                    yaxis: { title: { text: "UMAP-2" }, showgrid: true, gridcolor: "#e2e8f0" },
                    zaxis: { title: { text: "UMAP-3" }, showgrid: true, gridcolor: "#e2e8f0" },
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
