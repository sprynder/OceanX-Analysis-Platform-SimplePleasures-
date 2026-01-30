CREATE TABLE rois (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    frame_id UUID NOT NULL REFERENCES frames(id) ON DELETE CASCADE,
    frame_idx INT NOT NULL,
    video_id UUID NOT NULL REFERENCES videos(id) ON DELETE CASCADE,
    x1 INT NOT NULL,
    y1 INT NOT NULL,
    x2 INT NOT NULL,
    y2 INT NOT NULL,
    cluster INT DEFAULT -1,
    roi_url TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);
