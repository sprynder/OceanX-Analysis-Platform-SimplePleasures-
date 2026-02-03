"use client";

import { useState } from "react";

type ClusterControlsProps = {
  videoId: string;
  onReclusterStart: () => void;
  onReclusterComplete: () => void;
};

type ClusterParams = {
  min_cluster_size: number;
  min_samples: number | null;
  cluster_selection_epsilon: number;
  max_cluster_size: number | null;
  cluster_selection_method: "eom" | "leaf";
  pca_components: number;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

export function ClusterControls({
  videoId,
  onReclusterStart,
  onReclusterComplete,
}: ClusterControlsProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isReclustering, setIsReclustering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Default values matching backend
  const [params, setParams] = useState<ClusterParams>({
    min_cluster_size: 5,
    min_samples: null,
    cluster_selection_epsilon: 0.0,
    max_cluster_size: null,
    cluster_selection_method: "eom",
    pca_components: 50,
  });

  const handleRecluster = async () => {
    if (!videoId) return;

    setIsReclustering(true);
    setError(null);
    onReclusterStart();

    try {
      console.log("[Recluster] Sending request with params:", params);
      
      const response = await fetch(`${API_BASE}/videos/${videoId}/recluster`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error(`Recluster failed: ${response.status}`);
      }

      const result = await response.json();
      console.log("[Recluster] Response:", result);

      // Wait a moment for clustering to complete
      setTimeout(() => {
        setIsReclustering(false);
        onReclusterComplete();
      }, 2000);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Reclustering failed";
      console.error("[Recluster] Error:", err);
      setError(message);
      setIsReclustering(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Clustering Controls</h2>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-sm text-slate-600 hover:text-slate-900 transition"
        >
          {isExpanded ? "Hide" : "Show"}
        </button>
      </div>

      {isExpanded && (
        <div className="mt-4 space-y-4">
          <p className="text-sm text-slate-600">
            Adjust HDBSCAN clustering parameters and rerun clustering without reprocessing the video.
          </p>

          <div className="grid gap-4 sm:grid-cols-2">
            {/* Min Cluster Size */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Min Cluster Size
              </label>
              <input
                type="number"
                min="2"
                value={params.min_cluster_size}
                onChange={(e) =>
                  setParams({ ...params, min_cluster_size: parseInt(e.target.value) || 2 })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-slate-500">
                Minimum number of points in a cluster (default: 5)
              </p>
            </div>

            {/* Min Samples */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Min Samples
              </label>
              <input
                type="number"
                min="1"
                placeholder="Auto (null)"
                value={params.min_samples ?? ""}
                onChange={(e) =>
                  setParams({
                    ...params,
                    min_samples: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-slate-500">
                Core point threshold (default: auto)
              </p>
            </div>

            {/* Cluster Selection Epsilon */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Cluster Selection Epsilon
              </label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={params.cluster_selection_epsilon}
                onChange={(e) =>
                  setParams({
                    ...params,
                    cluster_selection_epsilon: parseFloat(e.target.value) || 0,
                  })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-slate-500">
                Distance threshold for merging clusters (default: 0.0)
              </p>
            </div>

            {/* Max Cluster Size */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Max Cluster Size
              </label>
              <input
                type="number"
                min="1"
                placeholder="Unlimited (null)"
                value={params.max_cluster_size ?? ""}
                onChange={(e) =>
                  setParams({
                    ...params,
                    max_cluster_size: e.target.value ? parseInt(e.target.value) : null,
                  })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-slate-500">
                Maximum cluster size (default: unlimited)
              </p>
            </div>

            {/* Cluster Selection Method */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Cluster Selection Method
              </label>
              <select
                value={params.cluster_selection_method}
                onChange={(e) =>
                  setParams({
                    ...params,
                    cluster_selection_method: e.target.value as "eom" | "leaf",
                  })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="eom">EOM (Excess of Mass)</option>
                <option value="leaf">Leaf</option>
              </select>
              <p className="mt-1 text-xs text-slate-500">
                Cluster extraction method (default: eom)
              </p>
            </div>

            {/* PCA Components */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                PCA Components
              </label>
              <input
                type="number"
                min="2"
                value={params.pca_components}
                onChange={(e) =>
                  setParams({ ...params, pca_components: parseInt(e.target.value) || 50 })
                }
                className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-slate-500">
                Dimensionality reduction before clustering (default: 50)
              </p>
            </div>
          </div>

          {error && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
              {error}
            </div>
          )}

          <button
            onClick={handleRecluster}
            disabled={isReclustering || !videoId}
            className="w-full rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed transition"
          >
            {isReclustering ? "Reclustering..." : "Recluster with These Parameters"}
          </button>
        </div>
      )}
    </div>
  );
}
