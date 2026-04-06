package repositories

import (
	"context"
	"database/sql"
	"oceanx/backend-go/internal/models"
)

// UpdateROIClusters updates the cluster_id and UMAP 3D coords for a batch of ROIs
func (r *VideoRepository) UpdateROIClusters(ctx context.Context, roiClusters []models.ROIClusterMapping) error {
	query := `UPDATE rois SET cluster = $1, umap_x = $2, umap_y = $3, umap_z = $4 WHERE id = $5`
	for _, rc := range roiClusters {
		_, err := r.DB.ExecContext(ctx, query, rc.ClusterID, rc.UmapX, rc.UmapY, rc.UmapZ, rc.RoiID)
		if err != nil {
			return err
		}
	}
	return nil
}

// GetROIsByVideo retrieves all ROIs for a given video
func (r *VideoRepository) GetROIsByVideo(ctx context.Context, videoID string) ([]models.Roi, error) {
	query := `SELECT id, frame_id, frame_idx, video_id, x1, y1, x2, y2, roi_url, cluster, umap_x, umap_y, umap_z
	          FROM rois WHERE video_id = $1 ORDER BY id`

	rows, err := r.DB.QueryContext(ctx, query, videoID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var rois []models.Roi
	for rows.Next() {
		var roi models.Roi
		var roiUrl sql.NullString

		err := rows.Scan(
			&roi.ID, &roi.FrameID, &roi.FrameIdx, &roi.VideoID,
			&roi.X1, &roi.Y1, &roi.X2, &roi.Y2, &roiUrl, &roi.Cluster,
			&roi.UmapX, &roi.UmapY, &roi.UmapZ,
		)
		if err != nil {
			return nil, err
		}

		if roiUrl.Valid {
			roi.RoiUrl = roiUrl.String
		}
		rois = append(rois, roi)
	}

	return rois, rows.Err()
}

// GetROIsByVideoAndCluster retrieves ROIs for a video filtered by cluster
func (r *VideoRepository) GetROIsByVideoAndCluster(ctx context.Context, videoID string, clusterID int) ([]models.Roi, error) {
	query := `SELECT id, frame_id, frame_idx, video_id, x1, y1, x2, y2, roi_url, cluster, umap_x, umap_y, umap_z
	          FROM rois WHERE video_id = $1 AND cluster = $2 ORDER BY id`

	rows, err := r.DB.QueryContext(ctx, query, videoID, clusterID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var rois []models.Roi
	for rows.Next() {
		var roi models.Roi
		var roiUrl sql.NullString

		err := rows.Scan(
			&roi.ID, &roi.FrameID, &roi.FrameIdx, &roi.VideoID,
			&roi.X1, &roi.Y1, &roi.X2, &roi.Y2, &roiUrl, &roi.Cluster,
			&roi.UmapX, &roi.UmapY, &roi.UmapZ,
		)
		if err != nil {
			return nil, err
		}

		if roiUrl.Valid {
			roi.RoiUrl = roiUrl.String
		}
		rois = append(rois, roi)
	}

	return rois, rows.Err()
}

// GetROIByID retrieves a single ROI by ID
func (r *VideoRepository) GetROIByID(ctx context.Context, roiID string) (*models.Roi, error) {
	query := `SELECT id, frame_id, frame_idx, video_id, x1, y1, x2, y2, roi_url, cluster, umap_x, umap_y, umap_z
	          FROM rois WHERE id = $1`

	var roi models.Roi
	var roiUrl sql.NullString

	err := r.DB.QueryRowContext(ctx, query, roiID).Scan(
		&roi.ID, &roi.FrameID, &roi.FrameIdx, &roi.VideoID,
		&roi.X1, &roi.Y1, &roi.X2, &roi.Y2, &roiUrl, &roi.Cluster,
		&roi.UmapX, &roi.UmapY, &roi.UmapZ,
	)

	if err == sql.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}

	if roiUrl.Valid {
		roi.RoiUrl = roiUrl.String
	}

	return &roi, nil
}

// GetClustersByVideo retrieves distinct clusters for a video with ROI count
type ClusterInfo struct {
	ClusterID int
	RoiCount  int
}

func (r *VideoRepository) GetClustersByVideo(ctx context.Context, videoID string) ([]ClusterInfo, error) {
	query := `SELECT cluster, COUNT(*) as roi_count
	          FROM rois WHERE video_id = $1 AND cluster >= 0
	          GROUP BY cluster ORDER BY cluster`

	rows, err := r.DB.QueryContext(ctx, query, videoID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var clusters []ClusterInfo
	for rows.Next() {
		var cluster ClusterInfo
		err := rows.Scan(&cluster.ClusterID, &cluster.RoiCount)
		if err != nil {
			return nil, err
		}
		clusters = append(clusters, cluster)
	}

	return clusters, rows.Err()
}
