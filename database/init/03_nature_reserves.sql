-- 03_nature_reserves.sql
-- Spatial table for nature reserves (example layer)

CREATE TABLE IF NOT EXISTS nature_reserves_bw (
    id SERIAL PRIMARY KEY,
    name TEXT,
    area_size DOUBLE PRECISION,
    geom GEOMETRY(MultiPolygon, 4326)
);

CREATE INDEX IF NOT EXISTS idx_nature_reserves_geom ON nature_reserves_bw USING GIST (geom);

-- Register the table in the metadata table. The `name` value matches the
-- spatial table name created above.
INSERT INTO layer_metadata (name, display_name, category, geometry_type)
VALUES ('nature_reserves_bw', 'Naturschutzgebiete', 'Environment', 'MultiPolygon')
ON CONFLICT (name) DO NOTHING;
