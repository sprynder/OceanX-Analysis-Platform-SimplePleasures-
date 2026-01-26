package repositories

import (
	"context"
	"database/sql"
	"time"

	"oceanx/backend-go/internal/models"

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
