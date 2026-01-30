package repositories

import (
	"context"
)

// UpdateROIClusters updates the cluster_id for a batch of ROIs
func (r *VideoRepository) UpdateROIClusters(ctx context.Context, roiClusters []struct {
	RoiID     string
	ClusterID int
}) error {
	query := `UPDATE rois SET cluster = $1 WHERE id = $2`
	for _, rc := range roiClusters {
		_, err := r.DB.ExecContext(ctx, query, rc.ClusterID, rc.RoiID)
		if err != nil {
			return err
		}
	}
	return nil
}
