package router

import (
	"github.com/gin-gonic/gin"
	"oceanx/backend-go/internal/handlers"
)

func SetupRouter(videoHandler *handlers.VideoHandler) *gin.Engine {
	r := gin.Default()
	r.POST("/videos", videoHandler.UploadVideo)

	return r
}


