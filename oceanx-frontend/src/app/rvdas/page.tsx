"use client";

import Link from "next/link";
import { ChangeEvent, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
  "http://localhost:8080";

type SavedTelemetryFile = {
  original_filename: string;
  stored_filename: string;
  stored_path: string;
  size_bytes: number;
};

type RejectedTelemetryFile = {
  filename: string;
  reason: string;
};

type IngestionResponse = {
  batch_id: string;
  batch_dir: string;
  saved_count: number;
  rejected_count: number;
  saved: SavedTelemetryFile[];
  rejected: RejectedTelemetryFile[];
};

export default function RvdasPage() {
  const [files, setFiles] = useState<File[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<IngestionResponse | null>(null);

  const selectedCount = files.length;
  const selectedSizeMb = useMemo(() => {
    const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
    return (totalBytes / (1024 * 1024)).toFixed(2);
  }, [files]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const list = event.target.files;
    if (!list) {
      setFiles([]);
      return;
    }
    setFiles(Array.from(list));
  };

  const uploadTelemetryFiles = async () => {
    if (files.length === 0) {
      setError("Select one or more .json/.txt files first.");
      return;
    }

    setUploading(true);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      for (const file of files) {
        formData.append("files", file);
      }

      const response = await fetch(`${API_BASE}/rvdas/ingest`, {
        method: "POST",
        body: formData,
      });

      const payload = (await response.json()) as IngestionResponse | { error?: string; details?: string; result?: IngestionResponse };

      if (!response.ok) {
        const message =
          "error" in payload && payload.error
            ? payload.error
            : `Upload failed (${response.status})`;
        const details = "details" in payload && payload.details ? `: ${payload.details}` : "";
        setError(`${message}${details}`);

        if ("result" in payload && payload.result) {
          setResult(payload.result);
        }
        return;
      }

      setResult(payload as IngestionResponse);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Upload request failed";
      setError(message);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-6 py-10">
        <header className="flex items-center justify-between gap-4">
          <div className="flex flex-col gap-2">
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-slate-500">
              OceanX
            </p>
            <h1 className="text-3xl font-semibold">OpenRVDAS Data Interface</h1>
            <p className="text-slate-600">
              Step 1 (Data ingestion): configure and run telemetry ingestion into your analytics pipeline.
            </p>
          </div>
          <Link
            href="/"
            className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100"
          >
            Back to Dashboard
          </Link>
        </header>

        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Ingestion Controls</h2>
          <p className="mt-2 text-sm text-slate-600">
            Upload telemetry files (`.json` / `.txt`) and store them on the backend local filesystem.
          </p>

          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-slate-700">Target cruise date</span>
              <input
                type="text"
                value="2021-07-06"
                readOnly
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700"
              />
            </label>

            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-slate-700">Source root</span>
              <input
                type="text"
                value="OpenRVDAS/raw + OpenRVDAS/proc"
                readOnly
                className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-700"
              />
            </label>
          </div>

          <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4">
            <label className="flex flex-col gap-2 text-sm">
              <span className="font-medium text-slate-700">Telemetry files</span>
              <input
                type="file"
                multiple
                accept=".json,.txt"
                onChange={onFileChange}
                className="rounded-lg border border-slate-200 bg-white px-3 py-2"
              />
            </label>

            <p className="mt-2 text-xs text-slate-600">
              Selected: {selectedCount} file(s), {selectedSizeMb} MB total
            </p>

            <button
              type="button"
              onClick={uploadTelemetryFiles}
              disabled={uploading || files.length === 0}
              className="mt-4 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {uploading ? "Uploading..." : "Upload to Local Storage"}
            </button>
          </div>

          <div className="mt-4 space-y-2 text-sm text-slate-700">
            <p>Pipeline loop target (based on your Step 22 flow):</p>
            <ul className="list-disc space-y-1 pl-5 text-slate-600">
              <li>Optional TXT → JSON conversion</li>
              <li>Daily pipeline build/check</li>
              <li>Parquet path resolution</li>
              <li>Downstream analysis/router execution</li>
            </ul>
          </div>

          {error ? (
            <div className="mt-6 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
              {error}
            </div>
          ) : null}

          {result ? (
            <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
              <p className="font-semibold">Ingestion complete</p>
              <p className="mt-1">Batch ID: {result.batch_id}</p>
              <p>Batch directory: {result.batch_dir}</p>
              <p>
                Saved: {result.saved_count}, Rejected: {result.rejected_count}
              </p>

              {result.saved.length > 0 ? (
                <div className="mt-3">
                  <p className="font-medium">Saved files</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-emerald-800">
                    {result.saved.map((item) => (
                      <li key={`${item.stored_filename}-${item.stored_path}`}>
                        {item.original_filename} → {item.stored_filename}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {result.rejected.length > 0 ? (
                <div className="mt-3">
                  <p className="font-medium">Rejected files</p>
                  <ul className="mt-1 list-disc space-y-1 pl-5 text-amber-800">
                    {result.rejected.map((item) => (
                      <li key={`${item.filename}-${item.reason}`}>
                        {item.filename}: {item.reason}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}
            </div>
          ) : null}

          <div className="mt-6 rounded-xl border border-slate-200 bg-white px-4 py-3 text-xs text-slate-500">
            API base: {API_BASE}
          </div>
        </section>
      </main>
    </div>
  );
}