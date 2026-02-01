import { useState } from "react";
import { Roi } from "@/types";
import { toMediaUrl } from "@/utils/media";

type AllROIsSectionProps = {
  rois: Roi[];
};

export function AllROIsSection({ rois }: AllROIsSectionProps) {
  const [showAllRois, setShowAllRois] = useState(false);

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">All ROIs</h2>
        <button
          onClick={() => setShowAllRois(!showAllRois)}
          className="text-sm text-slate-600 hover:text-slate-900 transition"
        >
          {showAllRois ? "Hide" : "Show"}
        </button>
      </div>
      {showAllRois &&
        (rois.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No ROIs found.</p>
        ) : (
          <div className="mt-4 flex flex-wrap gap-3">
            {rois.map((roi) => (
              <div
                key={roi.id}
                className="w-48 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600"
              >
                <div className="font-semibold text-slate-800">ROI {roi.id}</div>
                <div className="mt-1">Cluster: {roi.cluster}</div>
                <div>Frame: {roi.frame_idx}</div>
                <div>
                  Box: ({roi.x1}, {roi.y1}) → ({roi.x2}, {roi.y2})
                </div>
                {roi.roi_url ? (
                  <img
                    src={toMediaUrl(roi.roi_url)}
                    alt={`ROI ${roi.id}`}
                    className="mt-2 aspect-square w-full rounded-md object-cover"
                  />
                ) : (
                  <div className="mt-2 rounded-md border border-dashed border-slate-200 px-2 py-3 text-center text-[11px] text-slate-400">
                    No ROI image
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
    </div>
  );
}
