package repositories

import (
	"context"
	"database/sql"
	"fmt"
	"oceanx/backend-go/internal/models"
	"time"

	"github.com/google/uuid"
)

type ClusteringSettingsRepository struct {
	DB *sql.DB
}

func NewClusteringSettingsRepository(db *sql.DB) *ClusteringSettingsRepository {
	return &ClusteringSettingsRepository{DB: db}
}

// GetByVideoID retrieves clustering settings for a video
func (r *ClusteringSettingsRepository) GetByVideoID(ctx context.Context, videoID uuid.UUID) (*models.ClusteringSettings, error) {
	query := `
		SELECT id, video_id, min_cluster_size, min_samples, cluster_selection_epsilon,
		       max_cluster_size, cluster_selection_method, pca_components, created_at, updated_at
		FROM clustering_settings
		WHERE video_id = $1
	`

	var settings models.ClusteringSettings
	err := r.DB.QueryRowContext(ctx, query, videoID.String()).Scan(
		&settings.ID,
		&settings.VideoID,
		&settings.MinClusterSize,
		&settings.MinSamples,
		&settings.ClusterSelectionEpsilon,
		&settings.MaxClusterSize,
		&settings.ClusterSelectionMethod,
		&settings.PCAComponents,
		&settings.CreatedAt,
		&settings.UpdatedAt,
	)

	if err != nil {
		if err == sql.ErrNoRows {
			return nil, nil // No settings found
		}
		return nil, fmt.Errorf("failed to get clustering settings: %w", err)
	}

	return &settings, nil
}

// CreateOrUpdate creates or updates clustering settings for a video
func (r *ClusteringSettingsRepository) CreateOrUpdate(ctx context.Context, settings *models.ClusteringSettings) error {
	query := `
		INSERT INTO clustering_settings 
		(id, video_id, min_cluster_size, min_samples, cluster_selection_epsilon,
		 max_cluster_size, cluster_selection_method, pca_components, created_at, updated_at)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
		ON CONFLICT (video_id) DO UPDATE SET
			min_cluster_size = $3,
			min_samples = $4,
			cluster_selection_epsilon = $5,
			max_cluster_size = $6,
			cluster_selection_method = $7,
			pca_components = $8,
			updated_at = $10
	`

	now := time.Now()
	_, err := r.DB.ExecContext(
		ctx,
		query,
		settings.ID.String(),
		settings.VideoID.String(),
		settings.MinClusterSize,
		settings.MinSamples,
		settings.ClusterSelectionEpsilon,
		settings.MaxClusterSize,
		settings.ClusterSelectionMethod,
		settings.PCAComponents,
		settings.CreatedAt,
		now,
	)

	if err != nil {
		return fmt.Errorf("failed to create or update clustering settings: %w", err)
	}

	return nil
}

// Delete removes clustering settings for a video
func (r *ClusteringSettingsRepository) Delete(ctx context.Context, videoID uuid.UUID) error {
	query := `DELETE FROM clustering_settings WHERE video_id = $1`

	_, err := r.DB.ExecContext(ctx, query, videoID.String())
	if err != nil {
		return fmt.Errorf("failed to delete clustering settings: %w", err)
	}

	return nil
}
