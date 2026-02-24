-- Enable PostGIS
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE layer_metadata (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(255) UNIQUE NOT NULL,    -- Technical ID (e.g., 'aspect-cosine-mean')
    display_name VARCHAR(255) NOT NULL,   -- Human name
    category VARCHAR(100),                -- 'Environment', 'Elevation', etc.
    layer_type VARCHAR(50) NOT NULL,      -- 'raster' or 'vector'
    file_path TEXT,                       -- Internal path: /data/Optimized_Raster/...
    
    -- Metadata for TiTiler/Mapbox
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 12,
    bbox GEOMETRY(Polygon, 4326),         -- Spatial extent of the layer
    
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_layer_metadata_slug ON layer_metadata(slug);
