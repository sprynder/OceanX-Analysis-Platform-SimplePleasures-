import { DashboardResponse } from "@/types";

type DashboardSummaryProps = {
  dashboard: DashboardResponse | null;
};

export function DashboardSummary({ dashboard }: DashboardSummaryProps) {
  return (
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
  );
}
