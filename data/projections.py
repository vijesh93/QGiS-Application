"""
Purpose: Projections 
Most base maps (Google, OSM) use EPSG:3857 (Web Mercator). 
If TIFF is in EPSG:4326 (WGS 84), the Tileserver or the Database must perform a "re-projection" on the fly 
to warp the image so it doesn't look stretched or shifted. 
This is why having GDAL in Docker container is so important—it handles that math.
"""