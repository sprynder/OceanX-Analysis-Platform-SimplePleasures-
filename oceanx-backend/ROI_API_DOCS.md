# ROI CRUD API Documentation

This document describes the ROI (Region of Interest) CRUD endpoints in the OceanX backend API.

## Overview

The ROI API allows you to:
- List all ROIs for a video
- Filter ROIs by cluster
- Retrieve individual ROI details
- View ROIs grouped by cluster for dashboard display

## Endpoints

### 1. List ROIs for a Video

**Endpoint:** `GET /videos/:id/rois`

**Description:** Retrieve all ROIs for a specific video

**Parameters:**
- `id` (path parameter, required): Video ID
- `cluster` (query parameter, optional): Cluster ID to filter ROIs

**Response:** 
```json
{
  "video_id": "uuid",
  "count": 15,
  "rois": [
    {
      "id": "uuid",
      "frame_id": "uuid",
      "frame_idx": 0,
      "video_id": "uuid",
      "x1": 100,
      "y1": 200,
      "x2": 300,
      "y2": 400,
      "roi_url": "/data/rois/video-uuid/roi-uuid.jpg",
      "cluster": 1
    }
  ]
}
```

**Examples:**

Get all ROIs for a video:
```bash
curl http://localhost:8080/videos/abc-123/rois
```

Get ROIs filtered by cluster:
```bash
curl http://localhost:8080/videos/abc-123/rois?cluster=2
```

---

### 2. Get Single ROI

**Endpoint:** `GET /rois/:roi_id`

**Description:** Retrieve details of a single ROI by ID

**Parameters:**
- `roi_id` (path parameter, required): ROI ID

**Response:**
```json
{
  "id": "uuid",
  "frame_id": "uuid",
  "frame_idx": 0,
  "video_id": "uuid",
  "x1": 100,
  "y1": 200,
  "x2": 300,
  "y2": 400,
  "roi_url": "/data/rois/video-uuid/roi-uuid.jpg",
  "cluster": 1
}
```

**Example:**
```bash
curl http://localhost:8080/rois/roi-uuid-123
```

---

### 3. Get Video Cluster Dashboard

**Endpoint:** `GET /videos/:id/dashboard`

**Description:** Retrieve all ROIs grouped by cluster for dashboard display

**Parameters:**
- `id` (path parameter, required): Video ID

**Response:**
```json
{
  "video_id": "abc-123",
  "clusters": [
    {
      "cluster_id": 0,
      "roi_count": 5,
      "rois": [
        {
          "id": "uuid",
          "frame_id": "uuid",
          "frame_idx": 0,
          "video_id": "uuid",
          "x1": 100,
          "y1": 200,
          "x2": 300,
          "y2": 400,
          "roi_url": "/data/rois/video-uuid/roi-uuid.jpg",
          "cluster": 0
        }
      ]
    },
    {
      "cluster_id": 1,
      "roi_count": 3,
      "rois": [
        {
          "id": "uuid",
          "frame_id": "uuid",
          "frame_idx": 5,
          "video_id": "uuid",
          "x1": 150,
          "y1": 250,
          "x2": 350,
          "y2": 450,
          "roi_url": "/data/rois/video-uuid/roi-uuid-2.jpg",
          "cluster": 1
        }
      ]
    }
  ]
}
```

**Example:**
```bash
curl http://localhost:8080/videos/abc-123/dashboard
```

---

## Complete API Flow

### 1. Upload Video
```bash
curl -X POST -F "file=@video.mp4" http://localhost:8080/videos
```

Response includes `video_id`.

### 2. Video Processing (Async)
- ML backend processes video and extracts ROIs
- ROIs are detected, embedded, and images saved to `/data/rois/{video_id}/{roi_id}.jpg`
- Results posted to `/videos/{video_id}/complete`

### 3. Clustering (Async)
- ML backend clusters ROI embeddings using HDBSCAN
- Results posted to `/videos/{video_id}/clusters`
- ROI cluster assignments stored in database

### 4. Query ROIs (Your Dashboard)
```bash
# Get all ROIs
curl http://localhost:8080/videos/abc-123/rois

# Get ROIs for cluster 0
curl http://localhost:8080/videos/abc-123/rois?cluster=0

# Get dashboard view (ROIs grouped by cluster)
curl http://localhost:8080/videos/abc-123/dashboard
```

---

## Database Schema

The ROI data is stored in the `rois` table:

```sql
CREATE TABLE rois (
  id UUID PRIMARY KEY,
  frame_id UUID REFERENCES frames(id),
  frame_idx INT,
  video_id UUID REFERENCES videos(id),
  x1 INT,
  y1 INT,
  x2 INT,
  y2 INT,
  roi_url TEXT,
  cluster INT
);
```

---

## Storage

ROI images are stored on disk at:
```
/data/rois/{video_id}/{roi_id}.jpg
```

This volume is persistent and mounted via Docker Compose.

---

## Implementation Notes

- All endpoints use the JSON response format
- Cluster values can be NULL for unclustered ROIs
- The `roi_url` field contains the relative path to the saved JPEG image
- Image serving requires either Nginx static file configuration or a separate file serving endpoint (not yet implemented)
