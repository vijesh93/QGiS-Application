# Purpose: When we load TIFF into PostGIS, the raster2pgsql tool reads that Affine Transform and CRS (Coordinate Reference System)
#  as seen in the Python script

"""
1. Raster Pyramiding (Overviews)
When dealing with large raster files (like satellite imagery or DEMs), rendering the full-resolution data at a zoomed-out scale is computationally expensive. PostGIS uses Overviews (raster pyramids) to solve this. 
Google Groups: https://postgis.net/docs/using_raster_dataman.html#:~:text=The%20raster2pgsql%20is%20a%20raster,supports%20use%20the%20%2DG%20switch.

How it works: You create reduced-resolution versions of your raster. For example, level 2 might be 1/4 the original size, and level 4 might be 1/16.
Creation: Use the raster2pgsql tool with the -l flag to generate these overviews during import.
Example command: raster2pgsql -I -C -e -Y -F -s 4326 -t 100x100 -l 2,4,8,16 image.tif public.raster_table | psql -d spatial_db
Benefits: Desktop GIS (like QGIS) and web servers can automatically fetch the low-resolution "overview" when you are zoomed out, making the map pan and zoom much faster. 

We can generate all levels in a single command using the -l flag followed by a comma-separated list of levels.
Example bash command: raster2pgsql -I -C -s 4326 -t 100x100 -l 2,4,8,16 original_image.tif public.my_raster | psql -d spatial_db

Are variations saved as different rows or different tables?
They are saved as separate tables, not different rows in the same table. 

The Main Table: Stores the original resolution (e.g., my_raster).
Overview Tables: For each level, PostGIS creates a new table named with the prefix o_<level>_. For example, o_2_my_raster, o_4_my_raster, etc..
Internal Rows: Within each of those tables, the image is broken into "tiles" (small squares, often 100x100 pixels). Each tile is stored as a single row. 

Why separate tables?
This structure allows GIS software like QGIS to quickly identify which table to query based on your current zoom level. Instead of scanning one massive table, it only reads from the table that matches the resolution you are currently looking at. 

Would you like to see how to query the database to see which overview tables have been created and their metadata?
"""

"""
IMPORTANT Conversation:
Q: tileserv even the right choice for this? I read it is only suitable for vectors and not for raster?
A: pg_tileserv is primarily a vector tile server. It is designed to turn PostGIS geometry (points, lines, polygons) into Mapbox Vector Tiles (MVT).
+1

While pg_tileserv can serve rasters by using a custom SQL function to wrap ST_AsPNG, it is not its "native" strength. For a project with 450 heavy GeoTIFF layers, you are touching the limits of what a basic function-wrapper can do.

The Problem with pg_tileserv for Raster
CPU Overhead: It has to run a database function to encode a PNG for every single tile request.

Missing "Image" Features: It lacks built-in support for "Color Ramping" (e.g., mapping pixel value 10 to Green and 50 to Red) unless you hardcode that logic into SQL.

The Better Choice: titiler or pg_raster_serv
If your primary data is GeoTIFF (Raster), industry standards have shifted toward TiTiler or specialized raster servers.

Why TiTiler is usually the "Pro" choice:
Cloud Optimized: It is built specifically for "Cloud Optimized GeoTIFFs" (COG).

Dynamic Styling: You can tell the API: "Hey, render this TIFF using the 'Viridis' color map," and it does it on the fly.

Direct File Access: It doesn't even need the pixels to be in the database. It can read the .tif file directly from your data/ folder (using the "Pyramids" we discussed) and serve it.

The "Hybrid" Architecture (My Recommendation)
Since you already have pg_tileserv in your compose file and it's great for Vector data (like your "Nature Reserves" metadata or boundaries), I suggest a dual-server approach:

pg_tileserv: Use this for your 02_schema.sql metadata and any vector boundaries.

TiTiler: Use this for the 450 GeoTIFF layers.


"""