package config

import "os"

type Config struct {
    PostgresDSN     string
    FastAPIBaseURL  string
    VideoDir        string
}

func Load() Config {
    return Config{
        PostgresDSN:    getenv("POSTGRES_DSN", "postgres://oceanx:oceanx@postgres:5432/oceanx?sslmode=disable"),
        FastAPIBaseURL: getenv("FASTAPI_BASE_URL", "http://localhost:8000"),
        VideoDir:       getenv("VIDEO_DIR", "/data/videos"),
    }
}

func getenv(k, d string) string {
    if v := os.Getenv(k); v != "" {
        return v
    }
    return d
}
