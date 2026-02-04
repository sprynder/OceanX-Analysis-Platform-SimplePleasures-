CREATE TABLE clustering_settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL UNIQUE REFERENCES videos(id) ON DELETE CASCADE,
    min_cluster_size INT NOT NULL DEFAULT 5,
    min_samples INT NOT NULL DEFAULT 5,
    cluster_selection_epsilon FLOAT NOT NULL DEFAULT 0.0,
    max_cluster_size INT NOT NULL DEFAULT 0,
    cluster_selection_method TEXT NOT NULL DEFAULT 'eom',
    pca_components INT NOT NULL DEFAULT 100,
    created_at TIMESTAMP NOT NULL DEFAULT now(),
    updated_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX idx_clustering_settings_video_id ON clustering_settings(video_id);
