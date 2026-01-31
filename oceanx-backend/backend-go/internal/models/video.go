package models

import (
	"database/sql"
	"time"
)

type Video struct {
	ID              string         `json:"id"`
	Filename        string         `json:"filename"`
	Path            string         `json:"path"`
	Status          string         `json:"status"`
	FramesProcessed int            `json:"frames_processed"`
	RoisDetected    int            `json:"rois_detected"`
	Error           sql.NullString `json:"error,omitempty"`
	CreatedAt       time.Time      `json:"created_at"`
}
