package services

import (
	"context"
	"fmt"
	"io"
	"mime/multipart"
	"os"
	"path/filepath"

	"oceanx/backend-go/internal/clients"
	"oceanx/backend-go/internal/models"
	"oceanx/backend-go/internal/repositories"
)

type VideoService struct {
	Repo       *repositories.VideoRepository
	MLClient   *clients.MLClient
	StorageDir string
}

func NewVideoService(
	repo *repositories.VideoRepository,
	mlClient *clients.MLClient,
	storageDir string,
) *VideoService {
	return &VideoService{
		Repo:       repo,
		MLClient:   mlClient,
		StorageDir: storageDir,
	}
}

func (s *VideoService) SaveUploadedVideo(
	ctx context.Context,
	fileHeader *multipart.FileHeader,
) (*models.Video, error) {

	// Open uploaded file
	src, err := fileHeader.Open()
	if err != nil {
		return nil, err
	}
	defer src.Close()

	// Ensure storage dir exists
	if err := os.MkdirAll(s.StorageDir, 0755); err != nil {
		return nil, err
	}

	// Create DB record FIRST (gives us video_id)
	video, err := s.Repo.Create(
		ctx,
		fileHeader.Filename,
		"", // path set after save
	)
	if err != nil {
		return nil, err
	}

	videoPath := filepath.Join(
		s.StorageDir,
		fmt.Sprintf("%s%s",
			video.ID,
			filepath.Ext(fileHeader.Filename),
		),
	)

	// Create destination file
	dst, err := os.Create(videoPath)
	if err != nil {
		return nil, err
	}
	defer dst.Close()

	// Copy bytes
	if _, err := io.Copy(dst, src); err != nil {
		return nil, err
	}

	// Update path (simple update query)
	_, err = s.Repo.DB.ExecContext(
		ctx,
		`UPDATE videos SET path=$1 WHERE id=$2`,
		videoPath,
		video.ID,
	)
	if err != nil {
		return nil, err
	}

	video.Path = videoPath
	return video, nil
}

func (s *VideoService) TriggerProcessingAsync(video *models.Video) {
	go func() {
		ctx := context.Background()

		// Mark as processing
		_ = s.Repo.UpdateStatus(ctx, video.ID, "processing")

		err := s.MLClient.ProcessVideo(
			ctx,
			video.ID,
			video.Path,
		)

		if err != nil {
			_ = s.Repo.UpdateStatus(ctx, video.ID, "failed")
			return
		}

		// ML pipeline will populate DB/Qdrant later
		_ = s.Repo.UpdateStatus(ctx, video.ID, "completed")
	}()
}
