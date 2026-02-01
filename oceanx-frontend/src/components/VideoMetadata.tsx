import { useMemo } from "react";
import { Video } from "@/types";

type VideoMetadataProps = {
  video: Video;
};

export function VideoMetadata({ video }: VideoMetadataProps) {
  const errorText = useMemo(() => {
    if (!video?.error) return null;
    if (typeof video.error === "string") return video.error;
    if ("String" in video.error && video.error.Valid) return video.error.String;
    return null;
  }, [video]);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <h2 className="text-lg font-semibold">Video metadata</h2>
      <dl className="mt-4 grid grid-cols-1 gap-4 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">ID</dt>
          <dd className="mt-1 break-all font-medium text-slate-900">
            {video.id}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            Filename
          </dt>
          <dd className="mt-1 font-medium text-slate-900">{video.filename}</dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            Status
          </dt>
          <dd className="mt-1 font-medium text-slate-900">{video.status}</dd>
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
  );
}
