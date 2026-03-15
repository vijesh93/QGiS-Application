# 🌍 Baden-Württemberg Geoportal

A high-performance, containerized Web GIS application for visualizing and managing geospatial raster layers for the region of Baden-Württemberg, Germany. Layers are served as Cloud Optimized GeoTIFFs (COGs) via TiTiler and rendered interactively in the browser using MapLibre GL JS.

---

## ✨ Features

- Interactive map powered by **MapLibre GL JS**
- Raster tile streaming via **TiTiler** (Cloud Optimized GeoTIFF)
- **Redis tile caching** — tiles cached for 24 hours for fast repeat loads
- **FastAPI** backend serving layer metadata from PostGIS
- Layer sidebar with **search, category grouping, and opacity controls**
- Active layers legend with per-layer opacity sliders and remove buttons
- Base map transparency control
- Vector tile support via **pg_tileserv** (for future vector layers)
- Fully containerized with **Docker Compose** — one command to start everything
- Hot-reload development workflow with bind-mounts
- **One-command data pipeline** — download, optimize, and register all layers automatically

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
├── data/                           # Data pipeline
│   ├── data_downloader/
│   │   └── dowloader.py            # Downloads raw TIFFs from PANGAEA
│   ├── data_files/
│   │   ├── Raster/                 # Raw downloaded TIFFs      (gitignored)
│   │   └── Optimized_Raster/       # COG-optimized TIFFs       (gitignored)
│   ├── setup_layers.py             # ⭐ One-command pipeline orchestrator
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

- **Docker Engine** (Linux) or **Docker Desktop** with WSL2 backend (Windows)
- **WSL2** strongly recommended on Windows for filesystem performance

> No local Python or GDAL installation needed — everything runs inside the containers.

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/vijesh93/QGiS-Application.git
cd QGiS-Application
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Then edit `.env` with your values:

```env
# Proxy — leave empty if not behind a corporate proxy
HTTP_PROXY=
HTTPS_PROXY=
NO_PROXY=

# Database
DB_USER=geoportal_user
DB_PASSWORD=your_secure_password
DB_PASSWORD_URL=your_secure_password
POSTGRES_DB=geoportal

# Host ports — what gets exposed on your machine
DB_HOST_PORT=5432
BACKEND_HOST_PORT=8000
FRONTEND_HOST_PORT=3000
TITILER_HOST_PORT=8080
TILESERV_HOST_PORT=7800

# Frontend
VITE_TITILER_URL=http://localhost:8080
VITE_API_URL=/api/v1
```

> **`DB_PASSWORD_URL`** must be the URL-percent-encoded version of your password if it contains special characters (`@`, `#`, `/` etc.). For plain alphanumeric passwords they are identical.

### 3. Start the stack

**Development** (hot-reload, bind-mounts, source maps):

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Production** (optimized builds, detached):

```bash
docker compose -f docker-compose.yml up --build -d
```

### 4. Verify services are running

```bash
docker compose ps
```

| Service | URL |
|---|---|
| **Frontend** | http://localhost:3000 |
| **Backend API docs** | http://localhost:8000/docs |
| **TiTiler** | http://localhost:8080/docs |
| **pg_tileserv** | http://localhost:7800 |

The app loads at this point but the map shows **no layers** — run the data pipeline next.

---

## 🗂️ Data Pipeline

The pipeline downloads SRTM-derived rasters from PANGAEA, converts them to Cloud Optimized GeoTIFF format, and registers their metadata in PostGIS. The frontend then shows them automatically.

```
PANGAEA data source
       │
       ▼
[1] dowloader.py ──────► data_files/Raster/            (raw GeoTIFFs)
       │
       ▼
[2] cog_optimizer.py ──► data_files/Optimized_Raster/  (COG GeoTIFFs)
       │
       ▼
[3] register_layers.py ► PostGIS layer_metadata table
       │
       ▼
  Frontend map shows layers 🗺️
```

### One-command pipeline (recommended)

`setup_layers.py` orchestrates all steps automatically. Run it inside the container — no local Python or GDAL needed:

```bash
docker exec -it geoportal-data-loader python setup_layers.py
```

That's it. The script prints coloured progress for each step and shows the app URL when done.

### Pipeline flags

Skip steps you've already completed:

```bash
# Files already downloaded? Skip to optimization
docker exec -it geoportal-data-loader python setup_layers.py --skip-download

# COGs already exist? Skip straight to registration
docker exec -it geoportal-data-loader python setup_layers.py --skip-download --skip-optimize

# Only re-register metadata (e.g. after changing category rules)
docker exec -it geoportal-data-loader python setup_layers.py --only-register

# Skip TiTiler validation (faster, useful in dev)
docker exec -it geoportal-data-loader python setup_layers.py --skip-validate
```

### Running individual scripts

Each script can also be run independently:

```bash
docker exec -it geoportal-data-loader python data_downloader/dowloader.py
docker exec -it geoportal-data-loader python cog_optimizer.py
docker exec -it geoportal-data-loader python check_if_cog.py
docker exec -it geoportal-data-loader python register_layers.py
```

> All scripts use `__file__`-based path resolution and work both inside the container and directly on the host (Windows / Linux / macOS) without modification.

---

## 🔄 Complete First-Run Workflow

```bash
# 1. Start the stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d

# 2. Confirm all containers are healthy
docker compose ps

# 3. Run the full data pipeline (~50 files, several GB — takes a while)
docker exec -it geoportal-data-loader python setup_layers.py

# 4. Open the app
# → http://localhost:3000
```

After step 3 completes, reload the browser — all registered layers appear in the sidebar.

---

## 🛑 Stopping the Stack

```bash
# Stop but keep data (DB and Redis volumes preserved)
docker compose -f docker-compose.yml -f docker-compose.dev.yml down

# Stop AND wipe all data — destructive, resets the DB
docker compose -f docker-compose.yml -f docker-compose.dev.yml down -v
```

---

## 🔧 Useful Commands

```bash
# Follow logs for all services
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f

# Follow logs for a specific service
docker compose logs -f backend
docker compose logs -f raster-server

# Rebuild a single service after code changes
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build frontend

# Open a shell in the data container
docker exec -it geoportal-data-loader bash

# Open a PostgreSQL shell
docker exec -it geoportal-db psql -U geoportal_user -d geoportal

# Check registered layers
docker exec -it geoportal-db psql -U geoportal_user -d geoportal \
  -c "SELECT slug, display_name, category FROM layer_metadata ORDER BY slug;"

# Manually validate a single COG via TiTiler
curl "http://localhost:8080/cog/validate?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif"
```

---

## 🌐 How Raster Tiles Work

```
Browser
  │
  │  GET http://localhost:8080/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png
  │        ?url=/data/data_files/Optimized_Raster/aspectcosine_1KMma_SRTM.tif
  │        &rescale=-1,1&colormap_name=viridis
  │
  ▼
TiTiler container
  │  reads COG tile from mounted volume (./data → /data)
  │  checks Redis cache first (24h TTL)
  ▼
Redis
  │
  ▼
PNG tile → MapLibre renders on map
```

The browser calls TiTiler directly on `VITE_TITILER_URL` (default `http://localhost:8080`). The Vite dev proxy (`/titiler/...` → `http://raster-server:80`) is available as a fallback but direct calls are used in practice to avoid proxy encoding issues.

---

## 🗄️ Database Schema

Core table: `layer_metadata`

| Column | Type | Description |
|---|---|---|
| `id` | serial | Primary key |
| `slug` | varchar | Unique identifier (filename stem) |
| `display_name` | varchar | Human-readable name shown in UI |
| `category` | varchar | Sidebar category (e.g. `Terrain`) |
| `layer_type` | varchar | `raster` or `vector` |
| `file_path` | text | Path as seen by raster-server container |
| `bbox` | geometry | WGS84 bounding box (PostGIS POLYGON) |
| `min_zoom` | integer | Minimum map zoom level |
| `max_zoom` | integer | Maximum map zoom level |
| `is_active` | boolean | Whether layer appears in the UI |
| `created_at` | timestamp | Registration timestamp |

---

## 🐛 Troubleshooting

**Frontend shows no layers after running the pipeline**
- Check backend is healthy: `docker compose logs backend`
- Verify rows exist: `docker exec -it geoportal-db psql -U geoportal_user -d geoportal -c "SELECT count(*) FROM layer_metadata;"`
- Hard refresh the browser: `Ctrl + Shift + R`

**`setup_layers.py` fails with `DATABASE_URL is not set`**
- The full stack must be running before the pipeline
- Check env vars: `docker exec geoportal-data-loader env | grep DATABASE`

**Tiles show grey / 500 errors in the Network tab**
- Confirm TiTiler can read the file: `curl "http://localhost:8080/cog/info?url=/data/data_files/Optimized_Raster/<file>.tif"`
- Check TiTiler logs: `docker compose logs raster-server`
- Re-run COG validation: `docker exec -it geoportal-data-loader python check_if_cog.py`

**Slow tile loading on first request**
- Expected — TiTiler reads and caches on first access. Repeat requests hit Redis and are instant.

**`network gis-network declared as external, but could not be found`**
- Always run both compose files together: `-f docker-compose.yml -f docker-compose.dev.yml`
- Never use `external: true` with a hardcoded `name:` — it breaks on machines with a different project folder name
- The `networks:` section in `docker-compose.dev.yml` should only contain `gis-network:` with no other properties

**Docker installed via snap (Linux) — containers won't stop or permission denied**
- This is a known snap Docker limitation. Uninstall it and install the official Engine:
```bash
sudo snap remove docker
# Then follow: https://docs.docker.com/engine/install/ubuntu/
```

**Windows: bind-mount permission or performance issues**
- Ensure Docker Desktop has file sharing enabled for your project drive
- For best performance move the project inside the WSL2 filesystem (`~/...`)

---

## 🗺️ Roadmap

- Phase 2: JWT-based authentication for private layers
- Phase 3: `pgvector` integration for semantic search of layer metadata
- Phase 4: GenAI "Map Assistant" — natural language queries over the layer catalogue
- Phase 5: Subcategory support in sidebar (schema + API + frontend grouping)
- Phase 6: Vector layer support via pg_tileserv (administrative boundaries, nature reserves)

---

## 📄 License

MIT — see `LICENSE` file.