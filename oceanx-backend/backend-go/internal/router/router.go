package router

import (
	"oceanx/backend-go/internal/handlers"

	"github.com/gin-gonic/gin"
)

func SetupRouter(videoHandler *handlers.VideoHandler) *gin.Engine {
	r := gin.Default()
	r.POST("/videos", videoHandler.UploadVideo)
	r.GET("/videos/:id", videoHandler.GetVideo)
	r.POST("/videos/:id/complete", videoHandler.CompleteProcessing)
	r.POST("/videos/:id/clusters", videoHandler.UpdateClusters)

	return r
}
