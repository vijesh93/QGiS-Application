# 🌍 Baden-Württemberg Geoportal

A high-performance, scalable Web GIS application designed to visualize and manage over 450 geospatial layers for the region of Baden-Württemberg, Germany.

---

**Overview**

This repository contains a containerized application that serves vector tiles from PostGIS and a React Map UI for interactive exploration. The design focuses on performance (vector tiles + client-side rendering), modularity, and developer ergonomics.

**Key features**

- Dynamic map rendering with MapLibre GL JS
- Tile-based architecture using `pg_tileserv` (streams only visible features)
- Backend API built with FastAPI (ready for future LLM integrations)
- Container-first workflow using Docker + Docker Compose

---

## 🛠️ Tech Stack

- **Frontend:** React, MapLibre GL JS
- **Backend:** Python, FastAPI
- **Database:** PostgreSQL 15, PostGIS
- **Tileserver:** `pg_tileserv` (or alternative like `t-rex`)
- **Server:** Nginx for reverse proxy
- **Containers:** Docker, Docker Compose

---

## Quick Start (Development)

These instructions assume a modern Linux or WSL2 + Docker Desktop environment. Windows users should prefer WSL2 for best filesystem performance.

1) Prerequisites

- Docker Desktop (with WSL2 backend on Windows)
- `make` (optional) — many convenient shortcuts are available in `Makefile`

2) Environment variables

Create a `.env` file in the project root (example):

```env
POSTGRES_USER=admin
POSTGRES_PASSWORD=securepassword123
POSTGRES_DB=geoportal
```

3) Start the development environment (hot-reload enabled)

```powershell
# from project root (PowerShell / WSL)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Open services:

- Frontend: http://localhost:3000
- Backend (FastAPI): http://localhost:8000/docs
- Tileserver: http://localhost:7800

4) Stop and remove containers

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

---

## Production (Build & Run)

Build optimized images and run the production compose:

```powershell
make build
make start
```

Or with plain Docker Compose:

```powershell
docker compose -f docker-compose.yml up --build -d
```

---

## Project Structure

```
.
├── backend/            # FastAPI source code & GIS logic
├── frontend/           # React source code & Map UI
├── database/           # SQL initialization & migration scripts
│   └── init/           # Auto-run on DB startup
├── nginx/              # Reverse proxy configs
├── Makefile            # Project command shortcuts
├── docker-compose.yml  # Main orchestration file
└── docker-compose.dev.yml # Development overrides (bind-mounts, reload)
```

---

## Adding / Importing Layers

Add layers exported from QGIS as SQL or GeoJSON. To auto-import at database startup, place SQL files in `database/init/` (they will be executed during DB container init).

If you prefer interactive import, use the DB shell:

```powershell
make db-shell
```

After import, update the `layer_metadata` table so the frontend sidebar lists the layer.

---

## Development Notes & Bind-mounts

- `docker-compose.dev.yml` uses bind mounts (`./backend:/app`, `./frontend:/app`) so edits on the host appear immediately in containers and vice versa.
- On Windows, ensure Docker Desktop can access your project drive or use WSL2 to avoid permission and performance issues.
- Bind mounts hide files that were copied into the image at build-time — this is expected in a dev workflow.

If filesystem performance is poor on macOS/Windows, consider:

- Using WSL2 (Windows) for native-like performance
- Mutagen or Docker Sync for accelerated file sync

---

## Common Commands

- `make dev` — start development stack (hot-reload)
- `make build` — build production images
- `make start` — start production services
- `make stop` — stop services
- `make clean` — remove containers and volumes (careful: wipes DB)
- `make logs` — follow logs

---

## Troubleshooting

- Database migration errors: check SQL files in `database/init/` and the DB container logs (`docker compose logs db`).
- Permissions on Windows: enable file sharing for the project drive or run containers inside WSL2.
- Slow frontend rebuilds: ensure `node_modules` is installed inside container (dev compose keeps `/app/node_modules` as container-only volume).

---

## Roadmap

- Phase 2: JWT-based authentication for private layers
- Phase 3: Integrate `pgvector` for semantic search of layer metadata
- Phase 4: Add a GenAI "Map Assistant" for natural language queries

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and linting locally
4. Open a pull request with a clear description

---

## License

Specify project license here (e.g. MIT) or add a `LICENSE` file.
