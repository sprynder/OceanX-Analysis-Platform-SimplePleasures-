import { useEffect, useState } from "react";
import { ClusterGroup } from "@/types";
import { ROICard } from "./ROICard";

type ClusterCardProps = {
  cluster: ClusterGroup;
  videoId: string;
  onNameUpdate?: (clusterId: number, clusterName: string) => void;
};

// const API_BASE =
//   process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ||
//   "http://localhost:8080";

export function ClusterCard({ cluster, videoId, onNameUpdate }: ClusterCardProps) {
  const sortedRois = [...cluster.rois].sort(
    (a, b) => a.frame_idx - b.frame_idx
  );

  // Get cluster name from first ROI (all ROIs in cluster have same name)
  const currentName = cluster.rois[0]?.cluster_name || "";
  const [clusterName, setClusterName] = useState(currentName);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (!isEditing) {
      setClusterName(currentName);
    }
  }, [currentName, isEditing]);

  const handleSave = async () => {
    if (clusterName === currentName) {
      setIsEditing(false);
      return;
    }

    setIsSaving(true);
    try {
      const response = await fetch(`/videos/${videoId}/clusters/name`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          cluster_id: cluster.cluster_id,
          cluster_name: clusterName,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update cluster name: ${response.status}`);
      }

      console.log(`[ClusterCard] Updated cluster ${cluster.cluster_id} name to: ${clusterName}`);
      setIsEditing(false);
      onNameUpdate?.(cluster.cluster_id, clusterName);
    } catch (err) {
      console.error("[ClusterCard] Error updating cluster name:", err);
      alert("Failed to update cluster name");
    } finally {
      setIsSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSave();
    } else if (e.key === "Escape") {
      setClusterName(currentName);
      setIsEditing(false);
    }
  };

  return (
    <div className="rounded-xl border border-slate-100 bg-slate-50 p-4 w-full overflow-auto">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className="text-sm font-semibold text-slate-900">
            Cluster {cluster.cluster_id}
          </div>
          {isEditing ? (
            <div className="flex items-center gap-1">
              <input
                type="text"
                value={clusterName}
                onChange={(e) => setClusterName(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={handleSave}
                autoFocus
                disabled={isSaving}
                className="px-2 py-1 text-xs border border-slate-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-slate-100"
                placeholder="Enter name..."
              />
              {isSaving && <span className="text-xs text-slate-500">Saving...</span>}
            </div>
          ) : (
            <button
              onClick={() => setIsEditing(true)}
              className="px-2 py-1 text-xs text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded transition"
            >
              {currentName || "+ Name"}
            </button>
          )}
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
