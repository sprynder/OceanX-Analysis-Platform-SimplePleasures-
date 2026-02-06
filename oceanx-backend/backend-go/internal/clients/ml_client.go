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
			Timeout: 5 * time.Minute,
		},
	}
}

type ProcessVideoRequest struct {
	VideoID        string `json:"video_id"`
	VideoPath      string `json:"video_path"`
	EmbeddingModel string `json:"embedding_model"`
}

func (c *MLClient) ProcessVideo(
	ctx context.Context,
	videoID string,
	videoPath string,
	embeddingModel string,
) error {

	payload := ProcessVideoRequest{
		VideoID:        videoID,
		VideoPath:      videoPath,
		EmbeddingModel: embeddingModel,
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
	VideoID                 string  `json:"video_id"`
	MinClusterSize          int     `json:"min_cluster_size"`
	MinSamples              *int    `json:"min_samples,omitempty"`
	ClusterSelectionEpsilon float64 `json:"cluster_selection_epsilon"`
	MaxClusterSize          *int    `json:"max_cluster_size,omitempty"`
	ClusterSelectionMethod  string  `json:"cluster_selection_method"`
	PCAComponents           int     `json:"pca_components"`
}

type ClusterParams struct {
	MinClusterSize          int
	MinSamples              *int
	ClusterSelectionEpsilon float64
	MaxClusterSize          *int
	ClusterSelectionMethod  string
	PCAComponents           int
}

func (c *MLClient) ClusterROIs(
	ctx context.Context,
	videoID string,
	params *ClusterParams,
) error {

	// Use defaults if no params provided
	if params == nil {
		params = &ClusterParams{
			MinClusterSize:          5,
			MinSamples:              nil,
			ClusterSelectionEpsilon: 0.0,
			MaxClusterSize:          nil,
			ClusterSelectionMethod:  "eom",
			PCAComponents:           50,
		}
	}

	payload := ClusterROIsRequest{
		VideoID:                 videoID,
		MinClusterSize:          params.MinClusterSize,
		MinSamples:              params.MinSamples,
		ClusterSelectionEpsilon: params.ClusterSelectionEpsilon,
		MaxClusterSize:          params.MaxClusterSize,
		ClusterSelectionMethod:  params.ClusterSelectionMethod,
		PCAComponents:           params.PCAComponents,
	}

	body, _ := json.Marshal(payload)
	fmt.Printf("[MLClient] Triggering clustering for video %s with params: %s\n", videoID, string(body))

	req, err := http.NewRequestWithContext(
		ctx,
		http.MethodPost,
		c.BaseURL+"/cluster-rois",
		bytes.NewBuffer(body),
	)
	if err != nil {
		fmt.Printf("[MLClient] Failed to create request: %v\n", err)
		return err
	}

	req.Header.Set("Content-Type", "application/json")

	fmt.Printf("[MLClient] Sending clustering request to %s\n", c.BaseURL+"/cluster-rois")
	resp, err := c.Client.Do(req)
	if err != nil {
		fmt.Printf("[MLClient] Clustering request failed: %v\n", err)
		return err
	}
	defer resp.Body.Close()

	fmt.Printf("[MLClient] Clustering response status: %d\n", resp.StatusCode)
	if resp.StatusCode >= 300 {
		return fmt.Errorf("ML clustering service returned %d", resp.StatusCode)
	}

	fmt.Printf("[MLClient] Clustering completed successfully for video: %s\n", videoID)
	return nil
}
