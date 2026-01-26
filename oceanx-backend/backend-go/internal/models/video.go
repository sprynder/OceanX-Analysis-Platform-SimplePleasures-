package models

import "time"

type Video struct {
	ID        string    `json:"id"`
	Filename  string    `json:"filename"`
	Path      string    `json:"path"`
	Status    string    `json:"status"`
	CreatedAt time.Time `json:"created_at"`
}