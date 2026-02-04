"use client";

import { useState } from "react";
import { Video, DashboardResponse } from "@/types";
import { VideoMetadata } from "@/components/VideoMetadata";
import { DashboardSummary } from "@/components/DashboardSummary";
import { ClusterCard } from "@/components/ClusterCard";
import { AllROIsSection } from "@/components/AllROIsSection";
import { FrameByFrameView } from "@/components/FrameByFrameView";
import { VideoList } from "@/components/VideoList";
import { VideoUpload } from "@/components/VideoUpload";
import { ProcessingProgress } from "@/components/ProcessingProgress";
import { ClusterControls } from "@/components/ClusterControls";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

export default function Home() {
  const [tab, setTab] = useState<"select" | "upload">("select");
  const [uploadVideoId, setUploadVideoId] = useState<string | null>(null);
  const [selectedVideoId, setSelectedVideoId] = useState<string | null>(null);
  const [videoId, setVideoId] = useState("");
  const [video, setVideo] = useState<Video | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDashboard = async (id: string) => {
    const trimmed = id.trim();
    if (!trimmed) {
      setError("Enter a video id.");
      return;
    }

    setLoading(true);
    setError(null);
    setVideo(null);
    setDashboard(null);

    try {
      console.log(`[Dashboard] Fetching video and dashboard for ID: ${trimmed}`);
      const [videoRes, dashboardRes] = await Promise.all([
        fetch(`${API_BASE}/videos/${trimmed}`),
        fetch(`${API_BASE}/videos/${trimmed}/dashboard`),
      ]);

      if (!videoRes.ok) {
        throw new Error(`Video request failed (${videoRes.status})`);
      }
      if (!dashboardRes.ok) {
        throw new Error(`Dashboard request failed (${dashboardRes.status})`);
      }

      const [videoJson, dashboardJson] = (await Promise.all([
        videoRes.json(),
        dashboardRes.json(),
      ])) as [Video, DashboardResponse];

      console.log("[Dashboard] Video data:", videoJson);
      console.log("[Dashboard] Dashboard data:", dashboardJson);
      console.log(
        `[Dashboard] Clusters: ${dashboardJson.clusters.length}, ROIs: ${dashboardJson.rois.length}`
      );

      setVideo(videoJson);
      setDashboard(dashboardJson);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Request failed";
      console.error("[Dashboard] Error:", message, err);
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleClusterNameUpdate = (clusterId: number, clusterName: string) => {
    setDashboard((prev) => {
      if (!prev) return prev;

      const updatedClusters = prev.clusters.map((cluster) => {
        if (cluster.cluster_id !== clusterId) return cluster;
        return {
          ...cluster,
          rois: cluster.rois.map((roi) => ({
            ...roi,
            cluster_name: clusterName,
          })),
        };
      });

      const updatedRois = prev.rois.map((roi) =>
        roi.cluster === clusterId
          ? { ...roi, cluster_name: clusterName }
          : roi
      );

      return {
        ...prev,
        clusters: updatedClusters,
        rois: updatedRois,
      };
    });
  };

  const escapeCsv = (value: unknown) => {
    if (value === null || value === undefined) return "";
    const str = String(value);
    return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
  };

  const saveDefaultClusteringSettings = async (videoId: string) => {
    try {
      const defaultSettings = {
        min_cluster_size: 5,
        min_samples: 5,
        cluster_selection_epsilon: 0.0,
        max_cluster_size: 0,
        cluster_selection_method: "eom",
        pca_components: 100,
      };

      await fetch(`${API_BASE}/videos/${videoId}/clustering-settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(defaultSettings),
      });
      console.log("[Settings] Default clustering settings saved for video:", videoId);
    } catch (err) {
      console.error("[Settings] Error saving default settings:", err);
    }
  };

  const handleExportRois = () => {
    if (!dashboard || dashboard.rois.length === 0) return;

    const headers = [
      "id",
      "frame_id",
      "frame_idx",
      "video_id",
      "x1",
      "y1",
      "x2",
      "y2",
      "roi_url",
      "cluster",
      "cluster_name",
    ];

    const sorted = [...dashboard.rois].sort((a, b) => {
      if (a.frame_idx !== b.frame_idx) return a.frame_idx - b.frame_idx;
      return a.id.localeCompare(b.id);
    });

    const rows = sorted.map((roi) => [
      roi.id,
      roi.frame_id,
      roi.frame_idx,
      roi.video_id,
      roi.x1,
      roi.y1,
      roi.x2,
      roi.y2,
      roi.roi_url,
      roi.cluster,
      roi.cluster_name,
    ].map(escapeCsv).join(","));

    const csv = [headers.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const link = document.createElement("a");
    link.href = url;
    link.download = `rois_${videoId || "video"}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-10">
        <header className="flex flex-col gap-2">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
            OceanX
          </p>
          <h1 className="text-3xl font-semibold">Video ROI Dashboard</h1>
          <p className="text-slate-600">
            Barebones UI to validate frontend ↔ backend requests.
          </p>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex gap-2 border-b border-slate-200">
            <button
              onClick={() => setTab("select")}
              className={`px-4 py-2 font-medium transition ${
                tab === "select"
                  ? "border-b-2 border-slate-900 text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Select Existing
            </button>
            <button
              onClick={() => setTab("upload")}
              className={`px-4 py-2 font-medium transition ${
                tab === "upload"
                  ? "border-b-2 border-slate-900 text-slate-900"
                  : "text-slate-500 hover:text-slate-700"
              }`}
            >
              Upload New
            </button>
          </div>

          {tab === "select" ? (
            <VideoList onSelectVideo={(id) => {
              setVideoId(id);
              setSelectedVideoId(id);
              loadDashboard(id);
            }} />
          ) : (
            <VideoUpload
              onUploadSuccess={(newVideoId) => {
                setVideoId(newVideoId);
                setUploadVideoId(newVideoId);
                // Save default clustering settings for new video
                saveDefaultClusteringSettings(newVideoId);
                loadDashboard(newVideoId);
              }}
            />
          )}

          <ProcessingProgress videoId={uploadVideoId} label="Upload progress" />
          <ProcessingProgress videoId={selectedVideoId} label="Selected video progress" />

          {error ? (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
              {error}
            </div>
          ) : null}
          <div className="mt-3 text-xs text-slate-500">
            API base: {API_BASE}
          </div>
        </section>

        {video ? (
          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <VideoMetadata video={video} />
            <DashboardSummary dashboard={dashboard} />
          </section>
        ) : null}

        {video && dashboard ? (
          <ClusterControls
            videoId={videoId}
            onReclusterStart={() => {
              console.log("[Page] Reclustering started");
            }}
            onReclusterComplete={() => {
              console.log("[Page] Reclustering complete, reloading dashboard");
              loadDashboard(videoId);
            }}
          />
        ) : null}

        {dashboard ? (
          <section className="grid gap-6 overflow-hidden">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm overflow-hidden">
              <div className="flex items-center justify-between gap-3">
                <h2 className="text-lg font-semibold">Clusters</h2>
                <button
                  onClick={handleExportRois}
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 hover:bg-slate-50"
                >
                  Export ROIs CSV
                </button>
              </div>
              <div className="mt-4 grid gap-4">
                {dashboard.clusters.length === 0 ? (
                  <p className="text-sm text-slate-500">No clusters found.</p>
                ) : (
                  dashboard.clusters.map((cluster) => (
                    <ClusterCard 
                      key={cluster.cluster_id} 
                      cluster={cluster} 
                      videoId={videoId}
                      onNameUpdate={handleClusterNameUpdate}
                    />
                  ))
                )}
              </div>
            </div>

            <FrameByFrameView dashboard={dashboard} />

            <AllROIsSection rois={dashboard.rois} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
