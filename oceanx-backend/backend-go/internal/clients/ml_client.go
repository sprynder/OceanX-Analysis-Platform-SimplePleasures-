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
	Algorithm               string  `json:"algorithm"`
	VideoID                 string  `json:"video_id"`
	MinClusterSize          int     `json:"min_cluster_size"`
	MinSamples              *int    `json:"min_samples,omitempty"`
	ClusterSelectionEpsilon float64 `json:"cluster_selection_epsilon"`
	MaxClusterSize          *int    `json:"max_cluster_size,omitempty"`
	ClusterSelectionMethod  string  `json:"cluster_selection_method"`
	PCAComponents           int     `json:"pca_components"`
	KMeansK                 int     `json:"kmeans_k"`
	KMeansSeed              int     `json:"kmeans_seed"`
	KMeansMaxIter           int     `json:"kmeans_max_iter"`
}

type ClusterParams struct {
	Algorithm               string
	MinClusterSize          int
	MinSamples              *int
	ClusterSelectionEpsilon float64
	MaxClusterSize          *int
	ClusterSelectionMethod  string
	PCAComponents           int
	KMeansK                 int
	KMeansSeed              int
	KMeansMaxIter           int
}

func (c *MLClient) ClusterROIs(
	ctx context.Context,
	videoID string,
	params *ClusterParams,
) error {

	// Use defaults if no params provided
	if params == nil {
		params = &ClusterParams{
			Algorithm:               "hdbscan",
			MinClusterSize:          5,
			MinSamples:              nil,
			ClusterSelectionEpsilon: 0.0,
			MaxClusterSize:          nil,
			ClusterSelectionMethod:  "eom",
			PCAComponents:           50,
			KMeansK:                 8,
			KMeansSeed:              42,
			KMeansMaxIter:           20,
		}
	}

	payload := ClusterROIsRequest{
		Algorithm:               params.Algorithm,
		VideoID:                 videoID,
		MinClusterSize:          params.MinClusterSize,
		MinSamples:              params.MinSamples,
		ClusterSelectionEpsilon: params.ClusterSelectionEpsilon,
		MaxClusterSize:          params.MaxClusterSize,
		ClusterSelectionMethod:  params.ClusterSelectionMethod,
		PCAComponents:           params.PCAComponents,
		KMeansK:                 params.KMeansK,
		KMeansSeed:              params.KMeansSeed,
		KMeansMaxIter:           params.KMeansMaxIter,
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
