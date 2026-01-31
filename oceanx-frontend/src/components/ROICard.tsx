import { Roi } from "@/types";
import { toMediaUrl } from "@/utils/media";

type ROICardProps = {
  roi: Roi;
};

export function ROICard({ roi }: ROICardProps) {
  return (
    <div className="flex-shrink-0 w-48 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600">
      <div className="font-semibold text-slate-800">ROI {roi.id}</div>
      <div className="mt-1">Frame: {roi.frame_idx}</div>
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
  );
}
