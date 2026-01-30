package router

import (
	"oceanx/backend-go/internal/handlers"

	"github.com/gin-gonic/gin"
)

func SetupRouter(videoHandler *handlers.VideoHandler) *gin.Engine {
	r := gin.Default()

	// Video endpoints
	r.POST("/videos", videoHandler.UploadVideo)
	r.GET("/videos/:id", videoHandler.GetVideo)
	r.POST("/videos/:id/complete", videoHandler.CompleteProcessing)
	r.POST("/videos/:id/clusters", videoHandler.UpdateClusters)

	// ROI endpoints
	r.GET("/videos/:id/rois", videoHandler.ListROIs)
	r.GET("/videos/:id/dashboard", videoHandler.GetVideoClusterDashboard)
	r.GET("/rois/:roi_id", videoHandler.GetROI)

	return r
}
