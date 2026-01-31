'use client';

import { useMemo, useState } from 'react';
import { DashboardResponse } from '@/types';
import { ROICard } from './ROICard';

interface FrameByFrameViewProps {
  dashboard: DashboardResponse;
}

export function FrameByFrameView({ dashboard }: FrameByFrameViewProps) {
  // Find min and max frame indices
  const frameRange = useMemo(() => {
    if (dashboard.rois.length === 0) {
      return { min: 0, max: 0 };
    }
    const indices = dashboard.rois.map((roi) => roi.frame_idx);
    return {
      min: Math.min(...indices),
      max: Math.max(...indices),
    };
  }, [dashboard.rois]);

  const [currentFrame, setCurrentFrame] = useState(frameRange.min);

  // Get all unique cluster IDs from the entire dataset
  const allClusterIds = useMemo(() => {
    const clusterSet = new Set(dashboard.clusters.map((c) => c.cluster_id));
    return Array.from(clusterSet)
      .map((id) => ({ id, num: parseInt(id, 10) }))
      .sort((a, b) => a.num - b.num)
      .map((item) => item.id);
  }, [dashboard.clusters]);

  // Filter and group ROIs by frame and cluster
  const frameData = useMemo(() => {
    const roisInFrame = dashboard.rois.filter((roi) => roi.frame_idx === currentFrame);

    // Group by cluster_id
    const grouped: Record<string, typeof roisInFrame> = {};
    allClusterIds.forEach((clusterId) => {
      grouped[clusterId] = [];
    });
    roisInFrame.forEach((roi) => {
      if (!grouped[roi.cluster]) {
        grouped[roi.cluster] = [];
      }
      grouped[roi.cluster].push(roi);
    });

    return grouped;
  }, [currentFrame, dashboard.rois, allClusterIds]);

  const totalRoisInFrame = Object.values(frameData).reduce((sum, rois) => sum + rois.length, 0);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm overflow-hidden h-[600px]">
      <div className="flex h-full flex-col gap-4">
        <div>
          <h2 className="text-lg font-semibold mb-2">Frame-by-Frame View</h2>
          <p className="text-sm text-slate-600 mb-4">
            Frame {currentFrame} of {frameRange.max} • {totalRoisInFrame} ROIs
          </p>

          {/* Slider */}
          <div className="space-y-2">
            <input
              type="range"
              min={frameRange.min}
              max={frameRange.max}
              value={currentFrame}
              onChange={(e) => setCurrentFrame(parseInt(e.target.value, 10))}
              className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-slate-900"
            />
            <div className="flex justify-between text-xs text-slate-500">
              <span>Frame {frameRange.min}</span>
              <span>Frame {frameRange.max}</span>
            </div>
          </div>
        </div>

        {/* Display ROIs grouped by cluster */}
        <div className="space-y-4 overflow-y-auto pr-1">
          {allClusterIds.map((clusterId) => {
            const rois = frameData[clusterId];
            return (
              <div key={clusterId} className="border border-slate-200 rounded-lg p-4">
                <h3 className="text-sm font-semibold text-slate-700 mb-3">
                  Cluster {clusterId} ({rois.length} ROI{rois.length !== 1 ? 's' : ''})
                </h3>
                <div className="-mx-4 px-4 overflow-x-auto pb-2">
                  {rois.length === 0 ? (
                    <div className="flex items-center justify-center py-8 text-slate-400 text-sm">
                      No ROIs in this frame
                    </div>
                  ) : (
                    <div className="flex gap-3">
                      {rois.map((roi) => (
                        <div key={roi.id} className="flex-shrink-0">
                          <ROICard roi={roi} />
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}



