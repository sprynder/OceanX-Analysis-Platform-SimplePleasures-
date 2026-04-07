package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

type MLClient struct {
	BaseURL string
	Client  *http.Client
}

func NewMLClient(baseURL string) *MLClient {
	return &MLClient{
		BaseURL: baseURL,
		Client: &http.Client{
			Timeout: 60 * time.Second, // BioCLIP inference can be slow on CPU
		},
	}
}

type ProcessVideoRequest struct {
	VideoID   string `json:"video_id"`
	VideoPath string `json:"video_path"`
}

func (c *MLClient) ProcessVideo(
	ctx context.Context,
	videoID string,
	videoPath string,
) error {

	payload := ProcessVideoRequest{
		VideoID:   videoID,
		VideoPath: videoPath,
	}

	body, _ := json.Marshal(payload)
	fmt.Println("Sending request to ML service with payload:", string(body))

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.BaseURL+"/process-video",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("ML service returned %d", resp.StatusCode)
	}

	return nil
}

type ClusterROIsRequest struct {
	VideoID        string `json:"video_id"`
	MinClusterSize int    `json:"min_cluster_size"`
	PCAComponents  int    `json:"pca_components"`
}

func (c *MLClient) ClusterROIs(
	ctx context.Context,
	videoID string,
) error {

	payload := ClusterROIsRequest{
		VideoID:        videoID,
		MinClusterSize: 5,
		PCAComponents:  50,
	}

	body, _ := json.Marshal(payload)
	fmt.Println("Triggering clustering for video:", videoID)

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.BaseURL+"/cluster-rois",
		bytes.NewBuffer(body),
	)
	if err != nil {
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("ML clustering service returned %d", resp.StatusCode)
	}

	fmt.Println("Clustering completed for video:", videoID)
	return nil
}

// --- Search ---

type MLSearchRequest struct {
	VideoID      *string `json:"video_id"`       // nil = search all videos
	Query        string  `json:"query"`
	TopK         int     `json:"top_k"`
	DedupEnabled bool    `json:"dedup_enabled"`
	TauTime      float64 `json:"tau_time"`
	TauIoU       float64 `json:"tau_iou"`
	TauEmb       float64 `json:"tau_emb"`
}

type MLSearchROIResult struct {
	ROIID        string    `json:"roi_id"`
	Score        float64   `json:"score"`
	TimestampSec float64   `json:"timestamp_sec"`
	BBox         []float64 `json:"bbox"`
	FrameIdx     int       `json:"frame_idx"`
	ROIUrl       string    `json:"roi_url"`
	VideoID      string    `json:"video_id"`
}

type MLSearchResponse struct {
	VideoID  *string             `json:"video_id"`
	Results  []MLSearchROIResult `json:"results"`
	RawCount int                 `json:"raw_count"`
}

// --- Global UMAP ---

type MLGlobalROI struct {
	ROIID    string  `json:"roi_id"`
	VideoID  string  `json:"video_id"`
	FrameIdx int     `json:"frame_idx"`
	ROIUrl   string  `json:"roi_url"`
	UmapX    float64 `json:"umap_x"`
	UmapY    float64 `json:"umap_y"`
	UmapZ    float64 `json:"umap_z"`
	Cluster  int     `json:"cluster"`
}

type MLGlobalUMAPResponse struct {
	ROIs       []MLGlobalROI `json:"rois"`
	VideoCount int           `json:"video_count"`
	ROICount   int           `json:"roi_count"`
}

func (c *MLClient) SearchROIs(ctx context.Context, req MLSearchRequest) (*MLSearchResponse, error) {
	body, _ := json.Marshal(req)

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/search-rois", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("ML search service returned %d", resp.StatusCode)
	}

	var result MLSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}

type MLImageSearchRequest struct {
	VideoID      *string `json:"video_id"`
	ImageB64     string  `json:"image_b64"`
	TopK         int     `json:"top_k"`
	DedupEnabled bool    `json:"dedup_enabled"`
	TauTime      float64 `json:"tau_time"`
	TauIoU       float64 `json:"tau_iou"`
	TauEmb       float64 `json:"tau_emb"`
}

func (c *MLClient) SearchROIsByImage(ctx context.Context, req MLImageSearchRequest) (*MLSearchResponse, error) {
	body, _ := json.Marshal(req)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/search-rois-by-image", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("ML image search returned %d", resp.StatusCode)
	}

	var result MLSearchResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}
	return &result, nil
}

type MLGlobalUMAPRequest struct {
	DedupEnabled bool    `json:"dedup_enabled"`
	TauTime      float64 `json:"tau_time"`
	TauIoU       float64 `json:"tau_iou"`
	TauEmb       float64 `json:"tau_emb"`
}

func (c *MLClient) GlobalUMAP(ctx context.Context, req MLGlobalUMAPRequest) (*MLGlobalUMAPResponse, error) {
	body, _ := json.Marshal(req)
	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, c.BaseURL+"/global-umap", bytes.NewBuffer(body))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")

	resp, err := c.Client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return nil, fmt.Errorf("ML global-umap service returned %d", resp.StatusCode)
	}

	var result MLGlobalUMAPResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return nil, err
	}

	return &result, nil
}
