package websocket

import (
	"log"
	"sync"

	"github.com/gorilla/websocket"
)

type ProgressEvent struct {
	Type            string `json:"type"`
	VideoID         string `json:"video_id"`
	FrameIndex      int    `json:"frame_index,omitempty"`
	FramesProcessed int    `json:"frames_processed,omitempty"`
	TotalFrames     int    `json:"total_frames,omitempty"`
	ROIsDetected    int    `json:"rois_detected,omitempty"`
	Message         string `json:"message,omitempty"`
	Status          string `json:"status,omitempty"`
}

type ClientConn struct {
	VideoID string
	Conn    *websocket.Conn
}

type Manager struct {
	clients    map[*ClientConn]bool
	register   chan *ClientConn
	broadcast  chan ProgressEvent
	unregister chan *ClientConn
	mu         sync.RWMutex
}

func NewManager() *Manager {
	return &Manager{
		clients:    make(map[*ClientConn]bool),
		register:   make(chan *ClientConn),
		broadcast:  make(chan ProgressEvent, 100),
		unregister: make(chan *ClientConn),
	}
}

func (m *Manager) Start() {
	go func() {
		for {
			select {
			case client := <-m.register:
				m.mu.Lock()
				m.clients[client] = true
				m.mu.Unlock()
				log.Printf("[WS] Client registered for video %s (total: %d)", client.VideoID, len(m.clients))

			case client := <-m.unregister:
				m.mu.Lock()
				if _, ok := m.clients[client]; ok {
					delete(m.clients, client)
					client.Conn.Close()
				}
				m.mu.Unlock()

			case event := <-m.broadcast:
				m.mu.RLock()
				count := 0
				for client := range m.clients {
					// Only send to clients subscribed to this video
					if client.VideoID == event.VideoID {
						if err := client.Conn.WriteJSON(event); err != nil {
							log.Printf("[WS] Error writing to client: %v", err)
							m.unregister <- client
						} else {
							count++
						}
					}
				}
				m.mu.RUnlock()
				log.Printf("[WS] Broadcast event type=%s to %d clients for video %s", event.Type, count, event.VideoID)
			}
		}
	}()
}

func (m *Manager) Register(client *ClientConn) {
	m.register <- client
}

func (m *Manager) Unregister(client *ClientConn) {
	m.unregister <- client
}

func (m *Manager) Broadcast(event ProgressEvent) {
	m.broadcast <- event
}
