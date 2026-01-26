package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/lib/pq"

	"oceanx/backend-go/internal/handlers"
	"oceanx/backend-go/internal/repositories"
	"oceanx/backend-go/internal/router"
	"oceanx/backend-go/internal/services"
)

func main() {
	db, err := sql.Open("postgres", os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatal(err)
	}

	videoRepo := repositories.NewVideoRepository(db)
	videoService := services.NewVideoService(
		videoRepo,
		"/data/videos",
	)
	videoHandler := handlers.NewVideoHandler(videoService)

	r := router.SetupRouter(videoHandler)

	r.Run(":8080")
}
