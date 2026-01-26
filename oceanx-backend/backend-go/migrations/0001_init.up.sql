CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    path TEXT NOT NULL,
    frames_processed INT NOT NULL DEFAULT 0,
    rois_detected INT NOT NULL DEFAULT 0,
    error TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);