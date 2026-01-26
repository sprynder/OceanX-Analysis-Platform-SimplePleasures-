CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE videos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'uploaded',
    path TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT now()
);