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
func (s *VideoService) GetVideo(
	ctx context.Context,
	id string,
) (*models.Video, error) {
	return s.Repo.GetByID(ctx, id)
}

func (s *VideoService) SaveProcessingResults(
	ctx context.Context,
	videoID string,
	response *models.ProcessVideoResponse,
) error {
	// Build frame and ROI data structures
	frames := make([]*models.Frame, 0)
	rois := make([]*models.Roi, 0)

	for _, frameData := range response.Frames {
		frames = append(frames, &models.Frame{
			ID:       frameData.ID,
			VideoID:  frameData.VideoID,
			FrameIdx: frameData.FrameIndex,
		})

		for _, roiData := range frameData.ROIs {
			rois = append(rois, &models.Roi{
				ID:       roiData.ID,
				FrameID:  frameData.ID,
				FrameIdx: frameData.FrameIndex,
				VideoID:  frameData.VideoID,
				X1:       roiData.X1,
				Y1:       roiData.Y1,
				X2:       roiData.X2,
				Y2:       roiData.Y2,
				RoiUrl:   roiData.RoiUrl,
			})
		}
	}

	// Save frames
	if err := s.Repo.SaveFrames(ctx, videoID, frames); err != nil {
		return fmt.Errorf("failed to save frames: %w", err)
	}

	// Save ROIs
	if err := s.Repo.SaveROIs(ctx, videoID, rois); err != nil {
		return fmt.Errorf("failed to save rois: %w", err)
	}

	// Update video with processing stats
	totalROIs := len(rois)
	if err := s.MarkCompleted(ctx, videoID, len(frames), totalROIs); err != nil {
		return fmt.Errorf("failed to mark video completed: %w", err)
	}

	return nil
}

func (s *VideoService) MarkCompleted(
	ctx context.Context,
	id string,
	frames int,
	rois int,
) error {
	_, err := s.Repo.DB.ExecContext(ctx, `
		UPDATE videos
		SET status='completed',
		    frames_processed=$1,
		    rois_detected=$2
		WHERE id=$3
	`, frames, rois, id)

	return err
}

func (s *VideoService) SaveClusterResults(
	ctx context.Context,
	videoID string,
	update *models.ROIClusterUpdate,
) error {
	// Convert to the format expected by the repository
	roiClusters := make([]struct {
		RoiID     string
		ClusterID int
	}, len(update.ROIClusters))

	for i, rc := range update.ROIClusters {
		roiClusters[i].RoiID = rc.RoiID
		roiClusters[i].ClusterID = rc.ClusterID
	}

	if err := s.Repo.UpdateROIClusters(ctx, roiClusters); err != nil {
		return fmt.Errorf("failed to update ROI clusters: %w", err)
	}

	return nil
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
