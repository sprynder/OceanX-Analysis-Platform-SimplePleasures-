package models

type MLFrameData struct {
	ID         string      `json:"id"`
	VideoID    string      `json:"video_id"`
	FrameIndex int         `json:"frame_index"`
	ROIs       []MLROIData `json:"rois"`
}

type MLROIData struct {
	ID     string `json:"id"`
	X1     int    `json:"x1"`
	Y1     int    `json:"y1"`
	X2     int    `json:"x2"`
	Y2     int    `json:"y2"`
	RoiUrl string `json:"roi_url"`
}

type ProcessVideoResponse struct {
	Frames []MLFrameData `json:"frames"`
}
