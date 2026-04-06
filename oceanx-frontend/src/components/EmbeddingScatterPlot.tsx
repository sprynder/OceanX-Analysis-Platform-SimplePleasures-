"use client";

// This component MUST be loaded via dynamic(() => import(...), { ssr: false })
// because Plotly uses browser-only APIs (WebGL, window) at module load time.

import { useState, useMemo, useRef, useCallback } from "react";
import Plot from "react-plotly.js";
import { type Roi } from "@/types";
import { toMediaUrl } from "@/utils/media";

type Props = {
  rois: Roi[];
  /** ROI IDs from a search result — rendered as a separate bright trace */
  highlightIds?: Set<string>;
};

function clusterColor(clusterId: number): string {
  if (clusterId === -1) return "rgba(150,150,150,0.25)";
  return `hsl(${(clusterId * 47) % 360}, 65%, 55%)`;
}

function clusterColorSolid(clusterId: number): string {
  if (clusterId === -1) return "rgb(150,150,150)";
  return `hsl(${(clusterId * 47) % 360}, 65%, 55%)`;
}

export default function EmbeddingScatterPlot({ rois, highlightIds }: Props) {
  const [hoveredRoi, setHoveredRoi] = useState<Roi | null>(null);
  const [clusterLabels, setClusterLabels] = useState<Record<number, string>>({});

  // Only use ROIs that have all three UMAP coords
  const plotRois = useMemo(
    () => rois.filter((r) => r.umap_x != null && r.umap_y != null && r.umap_z != null),
    [rois]
  );

  const roiMap = useMemo(
    () => new Map(plotRois.map((r) => [r.id, r])),
    [plotRois]
  );

  const byCluster = useMemo(() => {
    const map = new Map<number, Roi[]>();
    for (const roi of plotRois) {
      const id = roi.cluster;
      if (!map.has(id)) map.set(id, []);
      map.get(id)!.push(roi);
    }
    return map;
  }, [plotRois]);

  const clusterIds = useMemo(
    () =>
      [...byCluster.keys()].sort((a, b) => {
        if (a === -1) return 1;
        if (b === -1) return -1;
        return a - b;
      }),
    [byCluster]
  );

  const clusterTraces = useMemo(
    () =>
      clusterIds.map((clusterId) => {
        const clusterRois = byCluster.get(clusterId)!;
        const label =
          clusterLabels[clusterId] ?? (clusterId === -1 ? "Noise" : `Cluster ${clusterId}`);
        return {
          type: "scatter3d" as const,
          mode: "markers" as const,
          name: label,
          x: clusterRois.map((r) => r.umap_x as number),
          y: clusterRois.map((r) => r.umap_y as number),
          z: clusterRois.map((r) => r.umap_z as number),
          customdata: clusterRois.map((r) => r.id),
          hovertemplate: "<extra></extra>",
          marker: {
            color: clusterColor(clusterId),
            size: clusterId === -1 ? 5 : 8,
            opacity: clusterId === -1 ? 0.5 : 0.85,
            line: clusterId === -1 ? { width: 0 } : { width: 0.5, color: "rgba(255,255,255,0.4)" },
          },
        };
      }),
    [clusterIds, byCluster, clusterLabels]
  );

  const searchHighlightTrace = useMemo(() => {
    if (!highlightIds || highlightIds.size === 0) return null;
    const matchedRois = plotRois.filter((r) => highlightIds.has(r.id));
    if (matchedRois.length === 0) return null;
    return {
      type: "scatter3d" as const,
      mode: "markers" as const,
      name: "Search results",
      x: matchedRois.map((r) => r.umap_x as number),
      y: matchedRois.map((r) => r.umap_y as number),
      z: matchedRois.map((r) => r.umap_z as number),
      customdata: matchedRois.map((r) => r.id),
      hovertemplate: "<extra></extra>",
      marker: {
        color: "#f59e0b",
        size: 9,
        opacity: 1,
        symbol: "diamond",
        line: { width: 1.5, color: "#ffffff" },
      },
    };
  }, [highlightIds, plotRois]);

  const traces = useMemo(
    () => (searchHighlightTrace ? [...clusterTraces, searchHighlightTrace] : clusterTraces),
    [clusterTraces, searchHighlightTrace]
  );

  // ─── Hover via direct DOM attachment ─────────────────────────────────────────
  // react-plotly.js attaches event listeners before Plotly.newPlot() resolves,
  // so the plotly_hover event silently drops until the next Plotly.react() call
  // (triggered by any data change). Fix: attach directly to the graphDiv inside
  // onInitialized (which fires AFTER newPlot resolves) and read live data via refs
  // so we never have a stale closure problem.

  // Keep refs pointing at current versions of the lookup tables
  const curveIdArraysRef = useRef<string[][]>([]);
  const roiMapRef = useRef<Map<string, Roi>>(new Map());
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

  if (plotRois.length === 0) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-semibold">Embedding Space (3D UMAP)</h2>
        <p className="mt-3 text-sm text-slate-500">
          No UMAP coordinates yet — run clustering to populate this view.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm overflow-hidden">
      <h2 className="text-lg font-semibold">Embedding Space (3D UMAP)</h2>
      <p className="mt-1 text-xs text-slate-500">
        {plotRois.length} ROIs across {clusterIds.filter((id) => id !== -1).length} clusters.
        Click legend to toggle · double-click to isolate · hover a point to preview.
        {searchHighlightTrace && (
          <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-50 px-2 py-0.5 font-medium text-amber-700">
            ◆ {highlightIds?.size} search match{highlightIds && highlightIds.size !== 1 ? "es" : ""} highlighted
          </span>
        )}
      </p>

      <div className="mt-4 flex gap-4 min-w-0 overflow-hidden">
        {/* 3D scatter */}
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
              legend: {
                x: 0.01, y: 0.99,
                bgcolor: "rgba(255,255,255,0.85)",
                bordercolor: "#e2e8f0", borderwidth: 1,
                font: { size: 12 },
              },
            }}
            onInitialized={handleInitialized}
            config={{ responsive: true, displayModeBar: false }}
            style={{ width: "100%" }}
            useResizeHandler
          />
        </div>

        {/* ROI preview panel */}
        <div className="w-52 shrink-0">
          {hoveredRoi ? (
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700 space-y-2">
              <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
                {hoveredRoi.roi_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={toMediaUrl(hoveredRoi.roi_url)}
                    alt="ROI preview"
                    className="w-full object-contain max-h-40"
                  />
                ) : (
                  <div className="flex h-28 items-center justify-center text-slate-400">no image</div>
                )}
              </div>
              <div className="space-y-1">
                <p>
                  <span className="font-medium">Cluster:</span>{" "}
                  <span
                    className="inline-block rounded px-1.5 py-0.5 text-white text-[10px]"
                    style={{ background: clusterColorSolid(hoveredRoi.cluster) }}
                  >
                    {clusterLabels[hoveredRoi.cluster] ??
                      (hoveredRoi.cluster === -1 ? "Noise" : `Cluster ${hoveredRoi.cluster}`)}
                  </span>
                </p>
                <p><span className="font-medium">Frame:</span> {hoveredRoi.frame_idx}</p>
                <p>
                  <span className="font-medium">Box:</span> ({hoveredRoi.x1},{hoveredRoi.y1}) →
                  ({hoveredRoi.x2},{hoveredRoi.y2})
                </p>
                <p className="truncate text-slate-400" title={hoveredRoi.id}>
                  {hoveredRoi.id.slice(0, 16)}…
                </p>
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-36 items-center justify-center rounded-xl border border-dashed border-slate-200 text-xs text-slate-400">
              hover a point
            </div>
          )}
        </div>
      </div>

      {/* Cluster label inputs */}
      {clusterIds.filter((id) => id !== -1).length > 0 && (
        <div className="mt-5 border-t border-slate-100 pt-4">
          <p className="mb-2 text-xs font-medium text-slate-500 uppercase tracking-wide">
            Label clusters
          </p>
          <div className="flex flex-wrap gap-2">
            {clusterIds
              .filter((id) => id !== -1)
              .map((id) => (
                <div key={id} className="flex items-center gap-1.5">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                    style={{ background: clusterColorSolid(id) }}
                  />
                  <input
                    value={clusterLabels[id] ?? `Cluster ${id}`}
                    onChange={(e) =>
                      setClusterLabels((prev) => ({ ...prev, [id]: e.target.value }))
                    }
                    className="w-32 rounded border border-slate-200 px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-slate-400"
                  />
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  );
}
