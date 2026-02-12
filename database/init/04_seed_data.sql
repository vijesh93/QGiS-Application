/* Example seed data. This file is idempotent and will not create duplicate
   metadata rows or duplicate features when run multiple times. */

-- Insert a dummy polygon (A square over part of BW) only if it doesn't exist
INSERT INTO nature_reserves_bw (name, geom)
SELECT 'Test Reserve', ST_GeomFromText('MULTIPOLYGON(((8.5 48.5, 9.0 48.5, 9.0 49.0, 8.5 49.0, 8.5 48.5)))', 4326)
WHERE NOT EXISTS (
    SELECT 1 FROM nature_reserves_bw WHERE name = 'Test Reserve'
);

-- Ensure the layer is registered in metadata (no duplicate names)
INSERT INTO layer_metadata (name, display_name, category, geometry_type)
VALUES ('nature_reserves_bw', 'Nature Reserves (Seed)', 'Environment', 'MultiPolygon')
ON CONFLICT (name) DO NOTHING;