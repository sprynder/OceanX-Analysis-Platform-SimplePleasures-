package handlers

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"oceanx/backend-go/internal/services"
)

type VideoHandler struct {
	Service *services.VideoService
}

func NewVideoHandler(service *services.VideoService) *VideoHandler {
	return &VideoHandler{Service: service}
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
	// go h.Service.ProcessVideo(video)

	c.JSON(http.StatusCreated, gin.H{
		"id":        video.ID,
		"filename":  video.Filename,
		"status":    video.Status,
		"createdAt": video.CreatedAt,
	})
}
