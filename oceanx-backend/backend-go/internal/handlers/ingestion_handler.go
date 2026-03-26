package handlers

import (
	"mime/multipart"
	"net/http"

	"oceanx/backend-go/internal/services"

	"github.com/gin-gonic/gin"
)

type IngestionHandler struct {
	Service *services.IngestionService
}

func NewIngestionHandler(service *services.IngestionService) *IngestionHandler {
	return &IngestionHandler{Service: service}
}

func (h *IngestionHandler) UploadTelemetryFiles(c *gin.Context) {
	if err := c.Request.ParseMultipartForm(512 << 20); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "invalid multipart payload",
			"details": err.Error(),
		})
		return
	}

	form, err := c.MultipartForm()
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "failed to parse multipart form",
			"details": err.Error(),
		})
		return
	}

	files := form.File["files"]
	if len(files) == 0 {
		if single, singleErr := c.FormFile("file"); singleErr == nil {
			files = []*multipart.FileHeader{single}
		}
	}

	if len(files) == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "at least one file is required (field name: files)",
		})
		return
	}

	result, saveErr := h.Service.SaveTelemetryFiles(files)
	if saveErr != nil {
		c.JSON(http.StatusInternalServerError, gin.H{
			"error":   "failed to save telemetry files",
			"details": saveErr.Error(),
		})
		return
	}

	if result.SavedCount == 0 {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "no valid files were saved",
			"result": result,
		})
		return
	}

	c.JSON(http.StatusCreated, result)
}