"use client";

import { useState, useEffect } from "react";

type ClusterControlsProps = {
  videoId: string;
  onReclusterStart: () => void;
  onReclusterComplete: () => void;
};

type ClusterParams = {
  algorithm: "hdbscan" | "kmeans";
  min_cluster_size: number;
  min_samples: number | null;
  cluster_selection_epsilon: number;
  max_cluster_size: number | null;
  cluster_selection_method: "eom" | "leaf";
  pca_components: number;
  kmeans_k: number;
  kmeans_seed: number;
  kmeans_max_iter: number;
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
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Default values matching backend
  const [params, setParams] = useState<ClusterParams>({
    algorithm: "hdbscan",
    min_cluster_size: 5,
    min_samples: null,
    cluster_selection_epsilon: 0.0,
    max_cluster_size: null,
    cluster_selection_method: "eom",
    pca_components: 50,
    kmeans_k: 8,
    kmeans_seed: 42,
    kmeans_max_iter: 20,
  });

  // Load clustering settings when video changes
  useEffect(() => {
    if (!videoId) return;

    const loadSettings = async () => {
      setIsLoading(true);
      try {
        const response = await fetch(`${API_BASE}/videos/${videoId}/clustering-settings`);
        if (response.ok) {
          const settings = await response.json();
          console.log("[ClusterControls] Loaded settings:", settings);
          setParams({
            algorithm: settings.algorithm || "hdbscan",
            min_cluster_size: settings.min_cluster_size || 5,
            min_samples: settings.min_samples || null,
            cluster_selection_epsilon: settings.cluster_selection_epsilon || 0.0,
            max_cluster_size: settings.max_cluster_size || null,
            cluster_selection_method: settings.cluster_selection_method || "eom",
            pca_components: settings.pca_components || 50,
            kmeans_k: settings.kmeans_k || 8,
            kmeans_seed: settings.kmeans_seed || 42,
            kmeans_max_iter: settings.kmeans_max_iter || 20,
          });
        }
      } catch (err) {
        console.error("[ClusterControls] Error loading settings:", err);
        // Keep default values on error
      } finally {
        setIsLoading(false);
      }
    };

    loadSettings();
  }, [videoId]);

  const getSettingsUpdatedAt = async (): Promise<string | null> => {
    const response = await fetch(`${API_BASE}/videos/${videoId}/clustering-settings`);
    if (!response.ok) return null;
    const settings = await response.json();
    return settings.updated_at ?? null;
  };

  const waitForReclusterCompletion = async (previousUpdatedAt: string | null) => {
    const maxChecks = 40;
    const intervalMs = 3000;

    for (let check = 0; check < maxChecks; check++) {
      await new Promise((resolve) => setTimeout(resolve, intervalMs));

      const latestUpdatedAt = await getSettingsUpdatedAt();
      if (!latestUpdatedAt) continue;

      if (!previousUpdatedAt) return;

      if (new Date(latestUpdatedAt).getTime() > new Date(previousUpdatedAt).getTime()) {
        return;
      }
    }

    throw new Error("Reclustering did not complete in time. Please refresh in a moment.");
  };

  const handleRecluster = async () => {
    if (!videoId) return;

    setIsReclustering(true);
    setError(null);
    onReclusterStart();

    try {
      const previousUpdatedAt = await getSettingsUpdatedAt();

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

      await waitForReclusterCompletion(previousUpdatedAt);
      onReclusterComplete();
      setIsReclustering(false);
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
            Choose clustering algorithm and rerun clustering without reprocessing the video.
          </p>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Algorithm
            </label>
            <select
              value={params.algorithm}
              onChange={(e) =>
                setParams({
                  ...params,
                  algorithm: e.target.value as "hdbscan" | "kmeans",
                })
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="hdbscan">HDBSCAN</option>
              <option value="kmeans">KMeans</option>
            </select>
            <p className="mt-1 text-xs text-slate-500">
              HDBSCAN is density-based; KMeans uses a fixed number of clusters.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            {params.algorithm === "hdbscan" && (
              <>
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
              </>
            )}

            {params.algorithm === "kmeans" && (
              <>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Number of Clusters (k)
                  </label>
                  <input
                    type="number"
                    min="2"
                    value={params.kmeans_k}
                    onChange={(e) =>
                      setParams({ ...params, kmeans_k: parseInt(e.target.value) || 2 })
                    }
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Target number of clusters (default: 8)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    KMeans Seed
                  </label>
                  <input
                    type="number"
                    value={params.kmeans_seed}
                    onChange={(e) =>
                      setParams({ ...params, kmeans_seed: parseInt(e.target.value) || 42 })
                    }
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Random seed for reproducible clustering (default: 42)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    KMeans Max Iterations
                  </label>
                  <input
                    type="number"
                    min="1"
                    value={params.kmeans_max_iter}
                    onChange={(e) =>
                      setParams({ ...params, kmeans_max_iter: parseInt(e.target.value) || 20 })
                    }
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Maximum KMeans iterations (default: 20)
                  </p>
                </div>
              </>
            )}

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
            {isReclustering
              ? "Reclustering..."
              : `Recluster with ${params.algorithm === "hdbscan" ? "HDBSCAN" : "KMeans"}`}
          </button>
        </div>
      )}
    </div>
  );
}
