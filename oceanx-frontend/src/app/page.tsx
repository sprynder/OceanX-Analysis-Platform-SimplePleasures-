"use client";

import { useMemo, useState } from "react";

type Roi = {
  id: string;
  frame_id: string;
  frame_idx: number;
  video_id: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  roi_url: string;
  cluster: number;
};

type ClusterGroup = {
  cluster_id: number;
  roi_count: number;
  rois: Roi[];
};

type DashboardResponse = {
  video_id: string;
  clusters: ClusterGroup[];
  rois: Roi[];
};

type Video = {
  id: string;
  filename: string;
  path: string;
  status: string;
  frames_processed: number;
  rois_detected: number;
  created_at: string;
  error?: { String: string; Valid: boolean } | string | null;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

const toMediaUrl = (input?: string | null) => {
  if (!input) return "";
  const normalized = input.replace(/\\/g, "/");
  if (normalized.startsWith("http://") || normalized.startsWith("https://")) {
    return normalized;
  }
  if (normalized.startsWith("/media/")) {
    return normalized;
  }
  // Videos: /data/videos/{video_id}.mp4 → /media/videos/{video_id}.mp4
  if (normalized.startsWith("/data/videos/")) {
    return `/media/videos/${normalized.replace("/data/videos/", "")}`;
  }
  // ROIs: /data/rois/{video_id}/{roi_id}.jpg → /media/rois/{video_id}/{roi_id}.jpg
  if (normalized.startsWith("/rois/")) {
    return `/media/rois/${normalized.replace("/rois/", "")}`;
  }
  return normalized;
};

export default function Home() {
  const [videoId, setVideoId] = useState("");
  const [video, setVideo] = useState<Video | null>(null);
  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const errorText = useMemo(() => {
    if (!video?.error) return null;
    if (typeof video.error === "string") return video.error;
    if ("String" in video.error && video.error.Valid) return video.error.String;
    return null;
  }, [video]);

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
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Video metadata</h2>
              <dl className="mt-4 grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    ID
                  </dt>
                  <dd className="mt-1 break-all font-medium text-slate-900">
                    {video.id}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    Filename
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {video.filename}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    Status
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {video.status}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    Created
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {new Date(video.created_at).toLocaleString()}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    Frames processed
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {video.frames_processed}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs uppercase tracking-wide text-slate-500">
                    ROIs detected
                  </dt>
                  <dd className="mt-1 font-medium text-slate-900">
                    {video.rois_detected}
                  </dd>
                </div>
              </dl>
              {errorText ? (
                <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700">
                  Error: {errorText}
                </div>
              ) : null}
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Dashboard summary</h2>
              <div className="mt-4 grid gap-3 text-sm">
                <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  Total clusters: {dashboard?.clusters.length ?? 0}
                </div>
                <div className="rounded-xl border border-slate-100 bg-slate-50 px-4 py-3">
                  Total ROIs: {dashboard?.rois.length ?? 0}
                </div>
              </div>
            </div>
          </section>
        ) : null}

        {dashboard ? (
          <section className="grid gap-6">
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">Clusters</h2>
              <div className="mt-4 grid gap-4">
                {dashboard.clusters.length === 0 ? (
                  <p className="text-sm text-slate-500">No clusters found.</p>
                ) : (
                  dashboard.clusters.map((cluster) => (
                    <div
                      key={cluster.cluster_id}
                      className="rounded-xl border border-slate-100 bg-slate-50 p-4"
                    >
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-semibold text-slate-900">
                          Cluster {cluster.cluster_id}
                        </div>
                        <div className="text-xs text-slate-500">
                          ROIs: {cluster.roi_count}
                        </div>
                      </div>
                      {cluster.rois.length > 0 ? (
                        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                          {cluster.rois.map((roi) => (
                            <div
                              key={roi.id}
                              className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600"
                            >
                              <div className="font-semibold text-slate-800">
                                ROI {roi.id}
                              </div>
                              <div className="mt-1">Frame: {roi.frame_idx}</div>
                              <div>
                                Box: ({roi.x1}, {roi.y1}) → ({roi.x2}, {roi.y2})
                              </div>
                              {roi.roi_url ? (
                                <img
                                  src={toMediaUrl(roi.roi_url)}
                                  alt={`ROI ${roi.id}`}
                                  className="mt-2 h-24 w-full rounded-md object-cover"
                                />
                              ) : (
                                <div className="mt-2 rounded-md border border-dashed border-slate-200 px-2 py-3 text-center text-[11px] text-slate-400">
                                  No ROI image
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="mt-2 text-xs text-slate-500">
                          No ROIs in this cluster.
                        </p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold">All ROIs</h2>
              {dashboard.rois.length === 0 ? (
                <p className="mt-3 text-sm text-slate-500">No ROIs found.</p>
              ) : (
                <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {dashboard.rois.map((roi) => (
                    <div
                      key={roi.id}
                      className="rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600"
                    >
                      <div className="font-semibold text-slate-800">
                        ROI {roi.id}
                      </div>
                      <div className="mt-1">Cluster: {roi.cluster}</div>
                      <div>Frame: {roi.frame_idx}</div>
                      <div>
                        Box: ({roi.x1}, {roi.y1}) → ({roi.x2}, {roi.y2})
                      </div>
                      {roi.roi_url ? (
                        <img
                          src={toMediaUrl(roi.roi_url)}
                          alt={`ROI ${roi.id}`}
                          className="mt-2 h-24 w-full rounded-md object-cover"
                        />
                      ) : (
                        <div className="mt-2 rounded-md border border-dashed border-slate-200 px-2 py-3 text-center text-[11px] text-slate-400">
                          No ROI image
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        ) : null}
      </main>
    </div>
  );
}
