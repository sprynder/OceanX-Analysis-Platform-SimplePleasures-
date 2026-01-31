package repositories

import (
	"context"
	"database/sql"
	"fmt"
	"oceanx/backend-go/internal/models"
	"time"

	"github.com/google/uuid"
)

type VideoRepository struct {
	DB *sql.DB
}

func NewVideoRepository(db *sql.DB) *VideoRepository {
	return &VideoRepository{DB: db}
}

func (r *VideoRepository) Create(
	ctx context.Context,
	filename string,
	path string,
) (*models.Video, error) {

	id := uuid.New().String()
	now := time.Now()

	query := `
		INSERT INTO videos (id, filename, path, status, created_at)
		VALUES ($1, $2, $3, 'uploaded', $4)
	`

	_, err := r.DB.ExecContext(
		ctx,
		query,
		id,
		filename,
		path,
		now,
	)
	if err != nil {
		return nil, err
	}

	return &models.Video{
		ID:        id,
		Filename:  filename,
		Path:      path,
		Status:    "uploaded",
		CreatedAt: now,
	}, nil
}

func (r *VideoRepository) UpdateStatus(
	ctx context.Context,
	videoID string,
	status string,
) error {
	_, err := r.DB.ExecContext(
		ctx,
		`UPDATE videos SET status=$1 WHERE id=$2`,
		status,
		videoID,
	)
	return err
}

func (r *VideoRepository) GetByID(
	ctx context.Context,
	id string,
) (*models.Video, error) {

	var v models.Video
	fmt.Println("Fetching video with ID:", id)
	query := `
		SELECT id, filename, path, status,
		       frames_processed, rois_detected,
		       error, created_at
		FROM videos
		WHERE id = $1::uuid
	`

	err := r.DB.QueryRowContext(ctx, query, id).Scan(
		&v.ID,
		&v.Filename,
		&v.Path,
		&v.Status,
		&v.FramesProcessed,
		&v.RoisDetected,
		&v.Error,
		&v.CreatedAt,
	)
	if err != nil {
		fmt.Println("Database error:", err)
		return nil, err
	}

	return &v, nil
}

func (r *VideoRepository) GetAll(ctx context.Context) ([]models.Video, error) {
	query := `
		SELECT id, filename, path, status,
		       frames_processed, rois_detected,
		       error, created_at
		FROM videos
		ORDER BY created_at DESC
	`

	rows, err := r.DB.QueryContext(ctx, query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	videos := make([]models.Video, 0)
	for rows.Next() {
		var v models.Video
		err := rows.Scan(
			&v.ID,
			&v.Filename,
			&v.Path,
			&v.Status,
			&v.FramesProcessed,
			&v.RoisDetected,
			&v.Error,
			&v.CreatedAt,
		)
		if err != nil {
			return nil, err
		}
		videos = append(videos, v)
	}

	return videos, rows.Err()
}

func (r *VideoRepository) SaveFrames(
	ctx context.Context,
	videoID string,
	frames []*models.Frame,
) error {
	query := `
		INSERT INTO frames (id, video_id, frame_idx)
		VALUES ($1, $2, $3)
		ON CONFLICT (video_id, frame_idx) DO NOTHING
	`

	for _, frame := range frames {
		_, err := r.DB.ExecContext(
			ctx,
			query,
			frame.ID,
			frame.VideoID,
			frame.FrameIdx,
		)
		if err != nil {
			return err
		}
	}

	return nil
}

func (r *VideoRepository) SaveROIs(
	ctx context.Context,
	videoID string,
	rois []*models.Roi,
) error {
	// First get the frame IDs for each frame_idx
	query := `
		INSERT INTO rois (id, frame_id, frame_idx, video_id, x1, y1, x2, y2, roi_url, cluster)
		VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
	`

	for _, roi := range rois {
		_, err := r.DB.ExecContext(
			ctx,
			query,
			roi.ID,
			roi.FrameID,
			roi.FrameIdx,
			videoID,
			roi.X1,
			roi.Y1,
			roi.X2,
			roi.Y2,
			roi.RoiUrl,
			-1, // Default cluster value for unclustered ROIs
		)
		if err != nil {
			return err
		}
	}

	return nil
}
