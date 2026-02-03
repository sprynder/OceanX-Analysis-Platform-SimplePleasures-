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

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

export default function Home() {
  const [tab, setTab] = useState<"select" | "upload">("select");
  const [videoId, setVideoId] = useState("");
  const [video, setVideo] = useState<Video | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);

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
              setIsProcessing(false);  // Not a new upload, just viewing
              loadDashboard(id);
            }} />
          ) : (
            <VideoUpload
              onUploadSuccess={(newVideoId) => {
                setVideoId(newVideoId);
                setIsProcessing(true);
                loadDashboard(newVideoId);
              }}
            />
          )}

          <ProcessingProgress videoId={videoId} isProcessing={isProcessing} />

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

            <FrameByFrameView dashboard={dashboard} />

            <AllROIsSection rois={dashboard.rois} />
          </section>
        ) : null}
      </main>
    </div>
  );
}
