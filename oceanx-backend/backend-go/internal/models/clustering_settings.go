package models

import (
	"time"

	"github.com/google/uuid"
)

type ClusteringSettings struct {
	ID                      uuid.UUID `json:"id"`
	VideoID                 uuid.UUID `json:"video_id"`
	MinClusterSize          int       `json:"min_cluster_size"`
	MinSamples              int       `json:"min_samples"`
	ClusterSelectionEpsilon float64   `json:"cluster_selection_epsilon"`
	MaxClusterSize          int       `json:"max_cluster_size"`
	ClusterSelectionMethod  string    `json:"cluster_selection_method"`
	PCAComponents           int       `json:"pca_components"`
	CreatedAt               time.Time `json:"created_at"`
	UpdatedAt               time.Time `json:"updated_at"`
}

// Default clustering settings
func DefaultClusteringSettings(videoID uuid.UUID) *ClusteringSettings {
	now := time.Now()
	return &ClusteringSettings{
		ID:                      uuid.New(),
		VideoID:                 videoID,
		MinClusterSize:          5,
		MinSamples:              5,
		ClusterSelectionEpsilon: 0.0,
		MaxClusterSize:          0,
		ClusterSelectionMethod:  "eom",
		PCAComponents:           100,
		CreatedAt:               now,
		UpdatedAt:               now,
	}
}
