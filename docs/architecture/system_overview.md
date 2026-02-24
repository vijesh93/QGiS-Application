# Architectural Design: Geospatial Layer Portal

## 1. Executive Summary
This project is a high-performance geospatial web application designed to visualize ~450 GeoTIFF raster layers. It uses a decoupled architecture to ensure that the heavy lifting of spatial data processing (Raster analysis) does not bottleneck the application logic.

## 2. System Architecture
The system follows a **Direct-to-Service** pattern for spatial data to maximize throughput and caching.



### Component Responsibilities

| Component | Technology | Primary Responsibility |
| :--- | :--- | :--- |
| **Frontend** | React / Vite | UI/UX, layer hierarchy management, and map rendering. Fetches tiles directly from `pg_tileserv`. |
| **Backend API** | FastAPI (Python) | **The Registry:** Manages discovery, metadata retrieval, and provides the "Tile URLs" to the frontend. |
| **Tileserver** | pg_tileserv | Specialized Go service that translates PostGIS raster data into web-ready PNG tiles on the fly. |
| **Spatial DB** | PostGIS | Stores raster pixels (TIFFs) in tiled format and maintains the `layer_metadata` directory. |
| **Data Loader** | Python / GDAL | (Dev Only) Ingests raw `.tif` files, extracts metadata, and populates the DB. |

## 3. Communication Patterns

### Layer Discovery Flow
1. **Frontend** requests `GET /api/v1/layers/categories`.
2. **Backend** queries `layer_metadata` and returns available folders (e.g., "Forestry", "Climate").
3. **Frontend** requests `GET /api/v1/layers?category=Forestry`.
4. **Backend** returns metadata for all layers in that folder, including a `tile_url` template.

### Map Rendering Flow
1. **Frontend** adds a layer to the map engine using the `tile_url`.
2. **Map Engine** calculates required XYZ tiles and fetches them directly from **pg_tileserv**.
3. **pg_tileserv** executes `ST_AsPNG` queries against **PostGIS** to stream pixel data.

## 4. Data Storage Strategy
To handle 450+ layers efficiently:
* **Metadata:** Stored in a central `layer_metadata` table for fast global searches and sidebar building.
* **Rasters:** Each TIFF is "tiled" into its own PostGIS table using a **One-Table-Per-Layer** strategy. This allows for spatial indexing and rapid partial-reads of large images.