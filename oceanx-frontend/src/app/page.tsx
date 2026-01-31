"use client";

import { useState } from "react";
import { Video, DashboardResponse } from "@/types";
import { VideoMetadata } from "@/components/VideoMetadata";
import { DashboardSummary } from "@/components/DashboardSummary";
import { ClusterCard } from "@/components/ClusterCard";
import { AllROIsSection } from "@/components/AllROIsSection";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

export default function Home() {
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
          <div className="flex flex-col gap-4 md:flex-row md:items-end">
            <div className="flex-1">
              <label className="text-sm font-medium text-slate-700">
                Video ID
              </label>
              <input
                value={videoId}
                onChange={(event) => setVideoId(event.target.value)}
                placeholder="e.g. 3d3c2e8c-..."
                className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none"
              />
            </div>
            <button
              onClick={() => loadDashboard(videoId)}
              className="rounded-xl bg-slate-900 px-6 py-2 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400"
              disabled={loading}
            >
              {loading ? "Loading..." : "Load dashboard"}
            </button>
          </div>
          <div className="mt-3 text-xs text-slate-500">
            API base: {API_BASE}
          </div>
          {error ? (
            <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-600">
              {error}
            </div>
          ) : null}
        </section>

        {video ? (
          <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <VideoMetadata video={video} />
            <DashboardSummary dashboard={dashboard} />
          </section>
        ) : null}

        {dashboard ? (
          <section className="grid gap-6 overflow-hidden">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm overflow-hidden">
              <h2 className="text-lg font-semibold">Clusters</h2>
              <div className="mt-4 grid gap-4">
                {dashboard.clusters.length === 0 ? (
                  <p className="text-sm text-slate-500">No clusters found.</p>
                ) : (
                  dashboard.clusters.map((cluster) => (
                    <ClusterCard key={cluster.cluster_id} cluster={cluster} />
                  ))
                )}
              </div>
            </div>

            <AllROIsSection rois={dashboard.rois} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
