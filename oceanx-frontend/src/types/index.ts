export type Roi = {
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

export type ClusterGroup = {
  cluster_id: number;
  roi_count: number;
  rois: Roi[];
};

export type DashboardResponse = {
  video_id: string;
  clusters: ClusterGroup[];
  rois: Roi[];
};

export type Video = {
  id: string;
  filename: string;
  path: string;
  status: string;
  frames_processed: number;
  rois_detected: number;
  created_at: string;
  error?: { String: string; Valid: boolean } | string | null;
};
