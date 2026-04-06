package models

type ROIClusterUpdate struct {
	VideoID     string              `json:"video_id"`
	ROIClusters []ROIClusterMapping `json:"roi_clusters"`
}

type ROIClusterMapping struct {
	RoiID     string  `json:"roi_id"`
	ClusterID int     `json:"cluster_id"`
	UmapX     float64 `json:"umap_x"`
	UmapY     float64 `json:"umap_y"`
	UmapZ     float64 `json:"umap_z"`
}
