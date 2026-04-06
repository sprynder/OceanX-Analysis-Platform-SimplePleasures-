package models

type Roi struct {
	ID       string   `json:"id"`
	FrameID  string   `json:"frame_id"`
	FrameIdx int      `json:"frame_idx"`
	VideoID  string   `json:"video_id"`
	X1       int      `json:"x1"`
	Y1       int      `json:"y1"`
	X2       int      `json:"x2"`
	Y2       int      `json:"y2"`
	RoiUrl   string   `json:"roi_url"`
	Cluster  int      `json:"cluster"`
	UmapX    *float64 `json:"umap_x"`
	UmapY    *float64 `json:"umap_y"`
	UmapZ    *float64 `json:"umap_z"`
}
