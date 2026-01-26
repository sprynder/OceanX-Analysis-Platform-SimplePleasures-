package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/lib/pq"

	"oceanx/backend-go/internal/clients"
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
	mlClient := clients.NewMLClient(
	os.Getenv("ML_SERVICE_URL"), // e.g. http://backend-ml:8000
)

	videoService := services.NewVideoService(
		videoRepo,
		mlClient,
		"/data/videos",
	)
	videoHandler := handlers.NewVideoHandler(videoService)

	r := router.SetupRouter(videoHandler)

	r.Run(":8080")
}
