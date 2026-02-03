package router

import (
	"oceanx/backend-go/internal/handlers"

	"github.com/gin-gonic/gin"
)

func SetupRouter(videoHandler *handlers.VideoHandler) *gin.Engine {
	r := gin.Default()

	// CORS middleware
	r.Use(func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(200)
			return
		}

		c.Next()
	})

	// Video endpoints
	r.GET("/videos", videoHandler.ListVideos)
	r.POST("/videos", videoHandler.UploadVideo)
	r.GET("/videos/:id", videoHandler.GetVideo)
	r.POST("/videos/:id/complete", videoHandler.CompleteProcessing)
	r.POST("/videos/:id/clusters", videoHandler.UpdateClusters)
	r.POST("/videos/:id/progress", videoHandler.ReceiveProgress)
	r.GET("/videos/:id/dashboard", videoHandler.GetVideoClusterDashboard)

	// WebSocket endpoint for real-time progress
	r.GET("/ws/videos/:id", videoHandler.WebSocketProgress)

	// ROI endpoints
	r.GET("/videos/:id/rois", videoHandler.ListROIs)
	r.GET("/rois/:roi_id", videoHandler.GetROI)

	return r
}
