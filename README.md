# 🌍 Baden-Württemberg Geoportal

A high-performance, containerized Web GIS application for visualizing and managing geospatial raster layers for the region of Baden-Württemberg, Germany. Layers are served as Cloud Optimized GeoTIFFs (COGs) via TiTiler and rendered interactively in the browser using MapLibre GL JS.

---

## ✨ Features

- Interactive map powered by **MapLibre GL JS**
- Raster tile streaming via **TiTiler** (Cloud Optimized GeoTIFF)
- **Redis tile caching** — tiles cached for 24 hours for fast repeat loads
- **FastAPI** backend serving layer metadata from PostGIS
- Layer sidebar with **search, category grouping, and opacity controls**
- Active layers legend with per-layer opacity sliders
- Base map transparency control
- Vector tile support via **pg_tileserv** (for future vector layers)
- Fully containerized with **Docker Compose** — one command to start everything
- Hot-reload development workflow with bind-mounts

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React, Vite, MapLibre GL JS, Tailwind CSS v4 |
| **Backend** | Python 3.11, FastAPI, SQLModel |
| **Database** | PostgreSQL 15 + PostGIS 3.3 |
| **Raster Server** | TiTiler (Cloud Optimized GeoTIFF streaming) |
| **Vector Tiles** | pg_tileserv |
| **Cache** | Redis 7 |
| **Data Pipeline** | Python, GDAL, rasterio, rio-cogeo |
| **Containers** | Docker, Docker Compose |

---

## 📁 Project Structure

```
.
├── backend/                        # FastAPI source code
│   ├── api/v1/layers.py            # Layer endpoints
│   ├── models/                     # SQLModel DB models
│   ├── repositories/               # SQL query logic
│   ├── services/                   # Business logic
│   ├── schemas/                    # Pydantic response schemas
│   ├── db.py                       # DB connection & session
│   ├── main.py                     # App entry point, CORS config
│   └── requirements.txt
│
├── frontend/                       # React app (Vite)
│   ├── src/
│   │   ├── api/layersApi.js        # Backend + TiTiler API calls
│   │   ├── components/
│   │   │   ├── Sidebar.jsx         # Layer browser & search
│   │   │   └── ActiveLayersLegend.jsx
│   │   ├── features/map/
│   │   │   ├── MapView.jsx         # MapLibre map component
│   │   │   └── hooks/useLayers.jsx # Layer state management
│   │   └── styles/index.css
│   └── vite.config.js              # Vite + proxy config
│
├── data/                           # Data pipeline scripts
│   ├── data_downloader/
│   │   └── dowloader.py            # Downloads raw TIFFs from PANGAEA
│   ├── data_files/
│   │   ├── Raster/                 # Raw downloaded TIFFs (gitignored)
│   │   └── Optimized_Raster/       # COG-optimized TIFFs (gitignored)
│   ├── cog_optimizer.py            # Converts Raster/ → Optimized_Raster/
│   ├── check_if_cog.py             # Validates COG compliance via TiTiler
│   └── register_layers.py          # Feeds layer metadata into PostGIS
│
├── database/
│   └── init/01_schema.sql          # Auto-runs on DB container startup
│
├── .env.example                    # Environment variable template
├── docker-compose.yml              # Production services
└── docker-compose.dev.yml          # Development overrides (hot-reload)
```

---

## ⚙️ Prerequisites

- **Docker Desktop** with WSL2 backend (Windows) or Docker Engine (Linux)
- **WSL2** recommended on Windows for filesystem performance
- **Python 3.11+** — only needed if running data pipeline scripts on the host (optional; scripts also run inside the container)
- **GDAL** — only needed on host if running optimizer outside Docker (`gdal-bin` is installed inside the container automatically)

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/vijesh93/QGiS-Application.git
cd QGiS-Application
```

### 2. Create your `.env` file

Copy the example and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env`:

```env
# Proxy (leave empty if not behind a corporate proxy)
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=

# Database
DB_USER=geoportal_user
DB_PASSWORD=your_secure_password
DB_PASSWORD_URL=your_secure_password   # URL-encoded if password has special chars
POSTGRES_DB=geoportal

# Host ports (what gets exposed on your machine)
DB_HOST_PORT=5432
BACKEND_HOST_PORT=8000
FRONTEND_HOST_PORT=3000
TITILER_HOST_PORT=8080
TILESERV_HOST_PORT=7800

# Frontend (points browser at TiTiler on host)
VITE_TITILER_URL=http://localhost:8080
VITE_API_URL=/api/v1
```

> **Note on `DB_PASSWORD_URL`:** If your password contains special characters (e.g. `@`, `#`, `/`), `DB_PASSWORD_URL` must be the URL-percent-encoded version. For a plain alphanumeric password they are identical.

### 3. Start the stack

**Development** (hot-reload, bind-mounts, source maps):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Production** (optimized builds):

```bash
docker compose -f docker-compose.yml up --build -d
```

### 4. Verify services are running

| Service | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **Backend API docs** | http://localhost:8000/docs |
| **TiTiler** | http://localhost:8080/docs |
| **pg_tileserv** | http://localhost:7800 |

At this point the app loads but the map will show **no layers** — you need to run the data pipeline first (see below).

---

## 🗂️ Data Pipeline — Adding Raster Layers

The pipeline has three steps: **Download → Optimize → Register**. Scripts work both on the host machine and inside the Docker container.

```
PANGAEA data source
       │
       ▼
[1] dowloader.py ──────► data/data_files/Raster/          (raw GeoTIFFs)
       │
       ▼
[2] cog_optimizer.py ──► data/data_files/Optimized_Raster/ (COG GeoTIFFs)
       │
       ▼
[3] register_layers.py ► PostGIS layer_metadata table
       │
       ▼
  Frontend map shows layers 🗺️
```

---

### Step 1 — Download raw rasters

The downloader fetches 1 km resolution SRTM-derived rasters (aspect, slope, elevation, roughness, TPI, TRI, VRM) from the PANGAEA data repository.

**Run inside the container** (recommended — no local Python setup needed):

```bash
docker exec -it geospatial-data-loader python data_downloader/dowloader.py
```

**Or run on the host** (requires `pip install requests`):

```bash
cd data
python data_downloader/dowloader.py
```

Files are saved to `data/data_files/Raster/`. Already-downloaded files are skipped automatically.

---

### Step 2 — Optimize to Cloud Optimized GeoTIFF (COG)

Raw GeoTIFFs must be converted to COG format before TiTiler can stream them efficiently as map tiles. This step:

- Converts each `.tif` in `Raster/` using `gdal_translate -of COG`
- Writes the result to `Optimized_Raster/`
- Skips files that are already optimized
- Validates each output file against TiTiler's `/cog/validate` endpoint

**Run inside the container** (recommended — GDAL is pre-installed):

```bash
docker exec -it geospatial-data-loader python cog_optimizer.py
```

**Or run on the host** (requires GDAL and `pip install requests`):

```bash
cd data
python cog_optimizer.py
```

> **Why COG?** A Cloud Optimized GeoTIFF stores internal tile pyramids (overviews) that allow TiTiler to read only the pixels needed for the current zoom level, without loading the entire file. This is what makes raster tile streaming fast.

You can also run the validator separately at any time to check the `Optimized_Raster/` folder:

```bash
docker exec -it geospatial-data-loader python check_if_cog.py
```

---

### Step 3 — Register layers in the database

This script reads each `.tif` from `Optimized_Raster/`, extracts spatial metadata (bounding box, zoom levels) via TiTiler, and inserts or updates a row in the `layer_metadata` table in PostGIS.

> **Important:** The stack must be running before this step so the script can reach TiTiler and PostgreSQL.

**Run inside the container:**

```bash
docker exec -it geospatial-data-loader python register_layers.py
```

**Or run on the host** (requires `pip install psycopg2-binary requests` and `DATABASE_URL` set):

```bash
cd data
DATABASE_URL=postgresql://geoportal_user:your_password@localhost:5432/geoportal \
python register_layers.py
```

After this step, **reload the frontend** at http://localhost:3000 — all registered layers will appear in the sidebar and can be toggled onto the map.

---

## 🔄 Full Workflow (copy-paste)

```bash
# 1. Start the stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# 2. Wait for all containers to be healthy
docker compose ps

# 3. Download raw rasters (~50 files, several GB — takes a while)
docker exec -it geospatial-data-loader python data_downloader/dowloader.py

# 4. Convert to COG
docker exec -it geospatial-data-loader python cog_optimizer.py

# 5. Register in database
docker exec -it geospatial-data-loader python register_layers.py

# 6. Open the app
# http://localhost:3000
```

---

## 🛑 Stopping the Stack

```bash
# Stop containers but keep volumes (DB data preserved)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Stop AND wipe all data (DB, Redis cache) — destructive!
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## 🔧 Common Commands

```bash
# Follow all logs
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Follow logs for a specific service
docker compose logs -f backend
docker compose logs -f raster-server

# Rebuild a single service after code changes
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build frontend

# Open a shell in the data container
docker exec -it geospatial-data-loader bash

# Open a PostgreSQL shell
docker exec -it qgis_layer_service-db-1 psql -U geoportal_user -d geoportal

# Check registered layers
docker exec -it qgis_layer_service-db-1 psql -U geoportal_user -d geoportal \
  -c "SELECT slug, category, layer_type FROM layer_metadata ORDER BY slug;"

# Manually validate a COG via TiTiler
curl "http://localhost:8080/cog/validate?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif"
```

---

## 🌐 How Raster Tiles Work (Architecture)

```
Browser
  │
  │  GET /titiler/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
  │        ?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif
  │        &rescale=-1,1&colormap_name=viridis
  │
  ▼
Vite dev proxy  (localhost:3000 → raster-server:80)
  │
  ▼
TiTiler container
  │  reads COG file from mounted volume
  │  checks Redis cache first
  ▼
Redis (tile cache, 24h TTL)
  │
  ▼
PNG tile returned to browser → MapLibre renders it on the map
```

The browser always calls TiTiler via the Vite proxy in development, which forwards requests from `/titiler/...` to `http://raster-server:80/...` inside the Docker network.

---

## 🗄️ Database Schema

The core table is `layer_metadata` in PostGIS:

| Column | Type | Description |
|---|---|---|
| `id` | serial | Primary key |
| `slug` | text | Unique identifier (filename stem) |
| `display_name` | text | Human-readable name shown in UI |
| `category` | text | Sidebar category (e.g. `Environment`) |
| `layer_type` | text | `raster` or `vector` |
| `file_path` | text | Path as seen by raster-server container |
| `bbox` | geometry | WGS84 bounding box (PostGIS POLYGON) |
| `min_zoom` | int | Minimum map zoom level |
| `max_zoom` | int | Maximum map zoom level |
| `is_active` | bool | Whether layer appears in the UI |
| `created_at` | timestamptz | Registration timestamp |

---

## 🐛 Troubleshooting

**Frontend shows no layers after registration**
- Check the backend is healthy: `docker compose logs backend`
- Verify rows exist: `SELECT count(*) FROM layer_metadata;`
- Hard refresh the browser: `Ctrl + Shift + R`

**Tiles show as grey / 500 errors in Network tab**
- Confirm TiTiler can access the file: `curl "http://localhost:8080/cog/info?url=/data/data_files/Optimized_Raster/<filename>.tif"`
- Check TiTiler logs: `docker compose logs raster-server`
- Verify the file is a valid COG: `docker exec -it geospatial-data-loader python check_if_cog.py`

**`register_layers.py` fails with connection error**
- The full stack must be running before registering layers
- Check `DATABASE_URL` is set: `docker exec geospatial-data-loader env | grep DATABASE`

**Slow tile loading on first request**
- Expected — TiTiler reads and caches on first access. Subsequent requests for the same tile are served from Redis and are fast.

**Windows: bind-mount permission errors**
- Ensure Docker Desktop has file sharing enabled for your project drive
- Or move the project inside your WSL2 filesystem (`/home/<user>/...`) for best performance

**Container can't resolve `raster-server` hostname**
- All services must be on the same Docker network (`gis-network`)
- Check: `docker inspect <container-name> | grep -A 10 Networks`

---

## 🗺️ Roadmap

- Phase 2: JWT-based authentication for private layers
- Phase 3: `pgvector` integration for semantic search of layer metadata
- Phase 4: GenAI "Map Assistant" — natural language queries over the layer catalogue
- Phase 5: Vector layer support via pg_tileserv (administrative boundaries, nature reserves)

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and linting locally
4. Open a pull request with a clear description

---

## 📄 License

MIT — see `LICENSE` file.
