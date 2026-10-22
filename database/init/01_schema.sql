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
    min_value DOUBLE PRECISION,           -- Real (nodata-excluded) band min, for TiTiler rescale
    max_value DOUBLE PRECISION,           -- Real (nodata-excluded) band max, for TiTiler rescale

    -- Time-series metadata: when band_count > 1, bands 1..band_count are real
    -- timesteps/values in source order (no synthetic band is ever added).
    -- band_start_date/band_date_step_days are set when the bands follow a
    -- parseable "<var>_<year>_<day-of-year>" date convention, starting at
    -- band 1. band_labels is set instead when the bands don't follow that
    -- convention but each still carries a real description (e.g. a
    -- qualitative sequence like "near"/"medium"/"far" prediction horizons).
    -- All three may be NULL (frontend falls back to plain "Band i of N").
    band_count INTEGER DEFAULT 1,
    band_start_date DATE,
    band_date_step_days INTEGER,
    band_labels TEXT[],

    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_layer_metadata_slug ON layer_metadata(slug);
