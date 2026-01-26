package handlers

import (
	"net/http"

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
			"error": "video not found",
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
