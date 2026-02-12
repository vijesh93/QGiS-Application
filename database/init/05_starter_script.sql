-- Enable PostGIS extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Layer Metadata Table
-- This stores the "definition" of your 450 QGIS layers
CREATE TABLE layer_metadata (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,        -- Technical table name
    display_name VARCHAR(255) NOT NULL, -- Human readable name
    category VARCHAR(100),             -- e.g., 'Environment', 'Transport'
    geometry_type VARCHAR(50),         -- Point, Line, or Polygon
    is_active BOOLEAN DEFAULT true,
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 22,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexing for speed
CREATE INDEX idx_layer_metadata_category ON layer_metadata(category);

-- Example Insert
INSERT INTO layer_metadata (name, display_name, category, geometry_type)
VALUES ('nature_reserves_bw', 'Nature Reserves BW', 'Environment', 'Polygon');