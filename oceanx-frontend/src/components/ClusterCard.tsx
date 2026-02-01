import { ClusterGroup } from "@/types";
import { ROICard } from "./ROICard";

type ClusterCardProps = {
  cluster: ClusterGroup;
};

export function ClusterCard({ cluster }: ClusterCardProps) {
  const sortedRois = [...cluster.rois].sort(
    (a, b) => a.frame_idx - b.frame_idx
  );

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 w-full overflow-auto">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-900">
          Cluster {cluster.cluster_id}
        </div>
        <div className="text-xs text-slate-500">ROIs: {cluster.roi_count}</div>
      </div>
      {cluster.rois.length > 0 ? (
        <div className="mt-3 -mx-4 px-4 overflow-x-scroll max-w-full">
          <div className="flex gap-3 pb-2 w-max">
            {sortedRois.map((roi) => (
              <ROICard key={roi.id} roi={roi} />
            ))}
          </div>
        </div>
      ) : (
        <p className="mt-2 text-xs text-slate-500">No ROIs in this cluster.</p>
      )}
    </div>
  );
}
