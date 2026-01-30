package handlers

import (
	"net/http"
	"strconv"

	"oceanx/backend-go/internal/models"
	"oceanx/backend-go/internal/services"

	"github.com/gin-gonic/gin"
)

type VideoHandler struct {
	Service *services.VideoService
}

func NewVideoHandler(service *services.VideoService) *VideoHandler {
	return &VideoHandler{Service: service}
}
func (h *VideoHandler) GetVideo(c *gin.Context) {
	id := c.Param("id")

	video, err := h.Service.GetVideo(
		c.Request.Context(),
		id,
	)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error":   "video not found",
			"details": err.Error(),
		})
		return
	}

	c.JSON(http.StatusOK, video)
}

func (h *VideoHandler) CompleteProcessing(c *gin.Context) {
	id := c.Param("id")

	var response models.ProcessVideoResponse
	if err := c.BindJSON(&response); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
		return
	}

	err := h.Service.SaveProcessingResults(
		c.Request.Context(),
		id,
		&response,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "processing results saved"})
}

func (h *VideoHandler) MarkCompleted(c *gin.Context) {
	id := c.Param("id")

	var payload struct {
		Frames int `json:"frames_processed"`
		Rois   int `json:"rois_detected"`
	}

	if err := c.BindJSON(&payload); err != nil {
		c.JSON(400, gin.H{"error": "invalid payload"})
		return
	}

	err := h.Service.MarkCompleted(
		c.Request.Context(),
		id,
		payload.Frames,
		payload.Rois,
	)
	if err != nil {
		c.JSON(500, gin.H{"error": err.Error()})
		return
	}

	c.JSON(200, gin.H{"status": "ok"})
}

func (h *VideoHandler) UpdateClusters(c *gin.Context) {
	id := c.Param("id")

	var update models.ROIClusterUpdate
	if err := c.BindJSON(&update); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid payload"})
		return
	}

	err := h.Service.SaveClusterResults(
		c.Request.Context(),
		id,
		&update,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"status": "clusters updated"})
}

func (h *VideoHandler) UploadVideo(c *gin.Context) {
	file, err := c.FormFile("file")
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "file is required",
		})
		return
	}

	video, err := h.Service.SaveUploadedVideo(
		c.Request.Context(),
		file,
	)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": err.Error(),
		})
		return
	}

	// 🔥 async ML kick-off goes HERE later
	h.Service.TriggerProcessingAsync(video)

	c.JSON(http.StatusCreated, gin.H{
		"id":        video.ID,
		"filename":  video.Filename,
		"status":    video.Status,
		"createdAt": video.CreatedAt,
	})
}

// ListROIs retrieves ROIs for a video, optionally filtered by cluster
func (h *VideoHandler) ListROIs(c *gin.Context) {
	videoID := c.Param("id")
	clusterParam := c.Query("cluster")

	var rois []models.Roi
	var err error

	if clusterParam != "" {
		// Filter by cluster
		clusterID, err := strconv.Atoi(clusterParam)
		if err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": "invalid cluster parameter"})
			return
		}
		rois, err = h.Service.GetROIsByVideoAndCluster(c.Request.Context(), videoID, clusterID)
	} else {
		// Get all ROIs for video
		rois, err = h.Service.GetROIsByVideo(c.Request.Context(), videoID)
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if rois == nil {
		rois = []models.Roi{} // Return empty array instead of null
	}

	c.JSON(http.StatusOK, gin.H{
		"video_id": videoID,
		"count":    len(rois),
		"rois":     rois,
	})
}

// GetROI retrieves a single ROI by ID
func (h *VideoHandler) GetROI(c *gin.Context) {
	roiID := c.Param("roi_id")

	roi, err := h.Service.GetROIByID(c.Request.Context(), roiID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	if roi == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "ROI not found"})
		return
	}

	c.JSON(http.StatusOK, roi)
}

// GetVideoClusterDashboard retrieves ROIs grouped by cluster
type ClusterGroup struct {
	ClusterID int          `json:"cluster_id"`
	RoiCount  int          `json:"roi_count"`
	ROIs      []models.Roi `json:"rois"`
}

type DashboardResponse struct {
	VideoID  string         `json:"video_id"`
	Clusters []ClusterGroup `json:"clusters"`
	ROIs     []models.Roi   `json:"rois"`
}

func (h *VideoHandler) GetVideoClusterDashboard(c *gin.Context) {
	videoID := c.Param("id")

	allROIs, err := h.Service.GetROIsByVideo(c.Request.Context(), videoID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}
	if allROIs == nil {
		allROIs = []models.Roi{}
	}

	// Get all clusters for the video
	clusters, err := h.Service.GetClustersByVideo(c.Request.Context(), videoID)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Build response with ROIs grouped by cluster
	clusterGroups := make([]ClusterGroup, 0)

	for _, cluster := range clusters {
		rois, err := h.Service.GetROIsByVideoAndCluster(c.Request.Context(), videoID, cluster.ClusterID)
		if err != nil {
			c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
			return
		}

		if rois == nil {
			rois = []models.Roi{}
		}

		clusterGroups = append(clusterGroups, ClusterGroup{
			ClusterID: cluster.ClusterID,
			RoiCount:  cluster.RoiCount,
			ROIs:      rois,
		})
	}

	c.JSON(http.StatusOK, DashboardResponse{
		VideoID:  videoID,
		Clusters: clusterGroups,
		ROIs:     allROIs,
	})
}
