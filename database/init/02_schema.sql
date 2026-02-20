"""
# Needs to be modified as per the following: To include raster and titiler supprt
CREATE TABLE IF NOT EXISTS layer_metadata (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,          -- Internal ID
    display_name TEXT NOT NULL,
    category TEXT,
    
    -- ARCHITECTURE PIVOT:
    -- Store the path to the file instead of the pixels in the DB
    file_path TEXT NOT NULL,            -- e.g., "/app/data/nature_reserves.tif"
    
    -- Metadata for the frontend
    geometry_type TEXT DEFAULT 'RASTER', -- 'RASTER' or 'VECTOR'
    srid INTEGER DEFAULT 4326,
    min_zoom INTEGER DEFAULT 0,
    max_zoom INTEGER DEFAULT 22,
    
    -- Bounding box for "Zoom to Layer" feature
    bbox_xmin DOUBLE PRECISION,
    bbox_ymin DOUBLE PRECISION,
    bbox_xmax DOUBLE PRECISION,
    bbox_ymax DOUBLE PRECISION,

    is_visible_by_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
"""

--
-- Schema: layer metadata and example spatial table
--
-- NOTE: This schema links metadata to spatial data by convention: the
-- `layer_metadata.name` value should match the PostGIS table name that
-- contains the features for this layer (for example 'nature_reserves_bw').
-- The application (frontend/backend) should use that value to construct
-- safe queries or tileserver URLs. Do NOT store feature geometries in the
-- metadata table itself.
--

CREATE TABLE IF NOT EXISTS layer_metadata (
    id SERIAL PRIMARY KEY,
    -- logical table name used by the application; should match the real
    -- PostGIS table that stores the features for this layer
    name TEXT NOT NULL,
    display_name TEXT NOT NULL,
    category TEXT,
    geometry_type TEXT,
    is_visible_by_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    CONSTRAINT uq_layer_metadata_name UNIQUE (name)
);

-- Index on category (idempotent)
CREATE INDEX IF NOT EXISTS idx_layer_metadata_category ON layer_metadata(category);

-- The spatial tables are defined in separate files (one file per layer)
-- to keep initialization modular. See `03_nature_reserves.sql` for the
-- example spatial table and registration.