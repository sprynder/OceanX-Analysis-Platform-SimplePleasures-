package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/lib/pq"

	"oceanx/backend-go/internal/clients"
	"oceanx/backend-go/internal/db"
	"oceanx/backend-go/internal/handlers"
	"oceanx/backend-go/internal/repositories"
	"oceanx/backend-go/internal/router"
	"oceanx/backend-go/internal/services"
	"oceanx/backend-go/internal/websocket"
)

func main() {
	databaseURL := os.Getenv("DATABASE_URL")

	// Run migrations first
	if err := db.RunMigrations(databaseURL); err != nil {
		log.Fatal(err)
	}

	db, err := sql.Open("postgres", databaseURL)
	if err != nil {
		log.Fatal(err)
	}

	videoRepo := repositories.NewVideoRepository(db)
	settingsRepo := repositories.NewClusteringSettingsRepository(db)
	mlClient := clients.NewMLClient(
		os.Getenv("ML_SERVICE_URL"), // e.g. http://backend-ml:8000
	)

	videoService := services.NewVideoService(
		videoRepo,
		settingsRepo,
		mlClient,
		"/data/videos",
	)

	// Initialize WebSocket manager
	wsManager := websocket.NewManager()
	wsManager.Start()

	videoHandler := handlers.NewVideoHandler(videoService, wsManager)

	r := router.SetupRouter(videoHandler)

	r.Run(":8080")
}
