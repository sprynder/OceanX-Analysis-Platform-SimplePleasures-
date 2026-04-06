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
  umap_x?: number | null;
  umap_y?: number | null;
  umap_z?: number | null;
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

export type SearchROIResult = {
  roi_id: string;
  score: number;
  timestamp_sec: number;
  bbox: number[];
  frame_idx: number;
  roi_url: string;
  video_id: string;
};

export type SearchResponse = {
  video_id: string | null;
  results: SearchROIResult[];
  raw_count: number;
};

export type GlobalRoi = {
  roi_id: string;
  video_id: string;
  frame_idx: number;
  roi_url: string;
  umap_x: number;
  umap_y: number;
  umap_z: number;
  cluster: number;
};

export type GlobalUMAPResponse = {
  rois: GlobalRoi[];
  video_count: number;
  roi_count: number;
};
