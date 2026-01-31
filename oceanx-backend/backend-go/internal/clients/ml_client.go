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
			Timeout: 10 * time.Second,
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
