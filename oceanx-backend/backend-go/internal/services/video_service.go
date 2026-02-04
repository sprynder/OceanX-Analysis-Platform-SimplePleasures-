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

	"github.com/google/uuid"
)

type VideoService struct {
	Repo         *repositories.VideoRepository
	SettingsRepo *repositories.ClusteringSettingsRepository
	MLClient     *clients.MLClient
	StorageDir   string
}

func NewVideoService(
	repo *repositories.VideoRepository,
	settingsRepo *repositories.ClusteringSettingsRepository,
	mlClient *clients.MLClient,
	storageDir string,
) *VideoService {
	return &VideoService{
		Repo:         repo,
		SettingsRepo: settingsRepo,
		MLClient:     mlClient,
		StorageDir:   storageDir,
	}
}

func (s *VideoService) GetAllVideos(ctx context.Context) ([]models.Video, error) {
	return s.Repo.GetAll(ctx)
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

	// Trigger clustering asynchronously with default parameters
	go s.TriggerClusteringAsync(videoID, nil)

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

func (s *VideoService) TriggerClusteringAsync(videoID string, params *clients.ClusterParams) {
	go func() {
		ctx := context.Background()
		fmt.Printf("[VideoService] Starting async clustering for video: %s\n", videoID)
		if params != nil {
			fmt.Printf("[VideoService] Clustering params: min_cluster_size=%d, method=%s, pca=%d\n",
				params.MinClusterSize, params.ClusterSelectionMethod, params.PCAComponents)
		} else {
			fmt.Printf("[VideoService] Using default clustering params\n")
		}

		err := s.MLClient.ClusterROIs(ctx, videoID, params)
		if err != nil {
			fmt.Printf("[VideoService] Clustering failed for video %s: %v\n", videoID, err)
			return
		}

		fmt.Printf("[VideoService] Clustering pipeline completed for video: %s\n", videoID)

		// Save clustering settings after successful clustering
		if params != nil {
			parsedID, err := uuid.Parse(videoID)
			if err != nil {
				fmt.Printf("[VideoService] Failed to parse video ID for settings save: %v\n", err)
				return
			}

			// Handle min_samples (could be nil)
			minSamples := 5 // default
			if params.MinSamples != nil {
				minSamples = *params.MinSamples
			}

			// Handle max_cluster_size (could be nil)
			maxClusterSize := 0 // default (means unlimited)
			if params.MaxClusterSize != nil {
				maxClusterSize = *params.MaxClusterSize
			}

			settings := &models.ClusteringSettings{
				ID:                      uuid.New(),
				VideoID:                 parsedID,
				MinClusterSize:          params.MinClusterSize,
				MinSamples:              minSamples,
				ClusterSelectionEpsilon: params.ClusterSelectionEpsilon,
				ClusterSelectionMethod:  params.ClusterSelectionMethod,
				PCAComponents:           params.PCAComponents,
				MaxClusterSize:          maxClusterSize,
			}

			err = s.SettingsRepo.CreateOrUpdate(ctx, settings)
			if err != nil {
				fmt.Printf("[VideoService] Failed to save clustering settings: %v\n", err)
			} else {
				fmt.Printf("[VideoService] Clustering settings saved for video: %s\n", videoID)
			}
		}
	}()
}

// ROI Query Methods

func (s *VideoService) GetROIsByVideo(
	ctx context.Context,
	videoID string,
) ([]models.Roi, error) {
	return s.Repo.GetROIsByVideo(ctx, videoID)
}

func (s *VideoService) GetROIsByVideoAndCluster(
	ctx context.Context,
	videoID string,
	clusterID int,
) ([]models.Roi, error) {
	return s.Repo.GetROIsByVideoAndCluster(ctx, videoID, clusterID)
}

func (s *VideoService) GetROIByID(
	ctx context.Context,
	roiID string,
) (*models.Roi, error) {
	return s.Repo.GetROIByID(ctx, roiID)
}

func (s *VideoService) GetClustersByVideo(
	ctx context.Context,
	videoID string,
) ([]repositories.ClusterInfo, error) {
	return s.Repo.GetClustersByVideo(ctx, videoID)
}

func (s *VideoService) UpdateClusterName(
	ctx context.Context,
	videoID string,
	clusterID int,
	clusterName string,
) error {
	return s.Repo.UpdateClusterName(ctx, videoID, clusterID, clusterName)
}

// GetClusteringSettings retrieves the saved clustering settings for a video
func (s *VideoService) GetClusteringSettings(
	ctx context.Context,
	videoID string,
) (*models.ClusteringSettings, error) {
	// Parse videoID to UUID
	parsedID, err := uuid.Parse(videoID)
	if err != nil {
		return nil, fmt.Errorf("invalid video ID: %w", err)
	}

	// Try to get existing settings
	settings, err := s.SettingsRepo.GetByVideoID(ctx, parsedID)
	if err != nil {
		return nil, err
	}

	// If no settings exist, return default settings
	if settings == nil {
		return models.DefaultClusteringSettings(parsedID), nil
	}

	return settings, nil
}

// SaveClusteringSettings saves clustering settings for a video
func (s *VideoService) SaveClusteringSettings(
	ctx context.Context,
	videoID string,
	settings *models.ClusteringSettings,
) error {
	// Parse videoID to UUID
	parsedID, err := uuid.Parse(videoID)
	if err != nil {
		return fmt.Errorf("invalid video ID: %w", err)
	}

	settings.VideoID = parsedID
	return s.SettingsRepo.CreateOrUpdate(ctx, settings)
}
