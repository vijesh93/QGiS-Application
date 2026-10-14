# Deployment Plan: QGiS-Application on an internet-facing VPS

> Supersedes an earlier draft of this file that planned a different scenario (a home
> Ubuntu VM behind a Cloudflare Tunnel). This version is for a VPS/server that already
> has Docker and nginx installed, with no domain yet, and is meant to host more than
> one app over time.

## Context

This repo is a containerized Web GIS app ("Baden-Württemberg Geoportal"): a React/Vite
frontend, a FastAPI backend (layer metadata API), PostGIS (metadata DB), TiTiler (raster
tile rendering from Cloud-Optimized GeoTIFFs), Redis (tile cache), and a one-shot
`data-loader` container for the download/optimize/register pipeline. There's also an
unused `tileserver` (pg_tileserv) service reserved for future vector layers.

As of starting this plan, the repo had no real production deployment path:
- The "production" `docker-compose.yml` had no `frontend`/`nginx` service at all.
- `frontend/Dockerfile` only ran the Vite **dev server**, never a built static bundle.
- `nginx/default.conf` was a 0-byte placeholder — no reverse proxy existed anywhere.
- Backend CORS was hardcoded to `localhost` origins.
- `db`, `tileserver`, and `raster-server` published ports straight to the host even in
  the "production" compose file — fine on a laptop, unsafe on the internet.
- There was no `docker-compose.prod.yml`; `make build` just reused the dev override.

This doc describes the production mode built to close those gaps, and how to deploy and
operate it, including hosting additional unrelated apps on the same server later.

**Decisions this plan assumes** (confirmed with the user when this was written):
- No domain yet — deploy over plain HTTP on the server's IP, with each app on its own
  port. A domain + HTTPS get added later, as a host-nginx-only change (see "Going from
  IP+HTTP to a domain + HTTPS" below).
- When a domain does exist, each app gets its own **subdomain** (not a shared domain
  with path prefixes).
- Server OS: Ubuntu/Debian (the exact commands below assume `apt`/`ufw`).
- The ~11GB of raster data is trial data today; the real dataset arrives later and the
  whole local-build → transfer → register workflow needs to be repeatable, not a
  one-off.

---

## Architecture: how this app is wired for production, and how multi-app hosting works

```
Internet ── host nginx (installed directly on the server, NOT in Docker; the only
             thing with a port open to the internet)
             │
             ├─ server block for THIS app   ── proxy_pass → 127.0.0.1:APP_GATEWAY_PORT
             ├─ server block for app #2     ── proxy_pass → 127.0.0.1:<its port>
             └─ ...
                                                      │
                                    Docker: "gateway" container (nginx, built from
                                    this repo's nginx/ folder) — the ONLY container
                                    port this app publishes, bound to 127.0.0.1 only
                                                      │
                               ┌──────────────┬───────────────────┐
                          frontend (static)  /api/v1/*         /titiler/*
                          served directly    → backend:8000    → raster-server:80
                          by the gateway            │
                                                     ▼
                                              db (PostGIS), redis — internal only,
                                              no published ports at all
```

Why this shape (written for someone without a networking background):

- **Host nginx is the single public door.** It's the only process with a port open to
  the internet. Every app behind it is reached by host nginx proxying to a port on
  `127.0.0.1` — i.e. the server talking to itself, never the internet talking to a
  container directly. Adding app #2 later = pick a new port + add one nginx file; app #1
  is untouched.
- **Each app publishes exactly one container port, bound to `127.0.0.1`.** Two reasons:
  (1) one memorable integration point per app no matter how many containers it has
  internally; (2) Docker rewrites `iptables` in ways that can bypass `ufw` rules for
  *published* ports — binding to `127.0.0.1` means the OS itself refuses the connection
  from outside, so safety doesn't depend on firewall rules alone.
- **Inside each app, a second nginx (in a container, built from this repo's `nginx/`
  folder) does the real routing**: serves the built frontend, proxies `/api/v1/*` to the
  backend, proxies `/titiler/*` to TiTiler. This replaces the old dev-only pattern of the
  frontend calling TiTiler directly on its own exposed port with everything on one
  origin — which also makes the backend's CORS allow-list a non-issue in practice
  (same-origin requests don't need CORS) and removes two public ports per app.
- **Moving to a domain + HTTPS later only touches host nginx.** Internal container ports
  never change — see the dedicated section near the end of this doc.

### The two nginx configs, and which is which

| | Where it runs | File in this repo | What it does |
|---|---|---|---|
| **Host nginx** | Directly on the server OS (`apt install nginx`, already done) | `deploy/host-nginx-app.conf.example` (template — real file lives on the server at `/etc/nginx/sites-available/<app>.conf`) | One server block per app. Public port in, `proxy_pass` to that app's `127.0.0.1:APP_GATEWAY_PORT`. Nothing else. |
| **Gateway nginx** | Inside Docker, one container per app, built from this repo | `nginx/Dockerfile` + `nginx/default.conf` | Serves the built frontend; proxies `/api/v1/` → `backend:8000` and `/titiler/` → `raster-server:80` over the app's internal Docker network. |

---

## Part A — Application changes made to enable a real production mode

- **`backend/main.py`**: CORS origins now come from a `CORS_ORIGINS` env var
  (comma-separated), falling back to the original localhost list when unset — dev is
  unaffected, prod sets it via `docker-compose.prod.yml`.
- **`docker-compose.yml`** (base): `db`, `tileserver`, `raster-server` no longer publish
  host ports — they're internal-only (`gis-network`), reached by `backend`/`gateway`.
  Also removed a `backend` `container_name` mismatch that existed between this file and
  the dev override.
- **`docker-compose.dev.yml`**: now adds back the host ports removed from the base file
  (`DB_HOST_PORT`, `TILESERV_HOST_PORT`, `TITILER_HOST_PORT`) since local dev still wants
  direct `curl`/`psql` access to them.
- **`docker-compose.prod.yml`** (new overlay): adds the `gateway` service (builds
  `nginx/Dockerfile`, publishes `127.0.0.1:${APP_GATEWAY_PORT}:80` only), sets
  `restart: unless-stopped` on the always-up services, wires `backend`'s `CORS_ORIGINS`
  to `${PUBLIC_APP_URL}`, and defines a prod-safe `data-loader` (no Jupyter port, no
  restart policy — it's a one-shot tool run via `run --rm`, not a long-running service).
- **`nginx/Dockerfile`** (new): multi-stage build — `node:20-slim` builds the frontend
  (`VITE_API_URL=/api/v1`, `VITE_TITILER_URL=/titiler`, both relative/same-origin now),
  then `nginx:alpine` serves the built `dist/` plus `nginx/default.conf`.
- **`nginx/default.conf`** (was empty): now the real gateway config described above.
- **`.env.example`**: added `PUBLIC_APP_URL` and `APP_GATEWAY_PORT` for the production
  overlay.
- **`deploy/host-nginx-app.conf.example`** (new): the host-nginx template referenced
  above and in the runbook below.

Run `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` any time to
sanity-check the merged production config before deploying.

---

## Part B — Getting code and data onto the server

**Code**: git, as planned. On the server: `git clone` (the repo's GitHub remote), then
`git pull` for updates. Never commit the real `.env` — create it directly on the server
from `.env.example` with fresh production values. **Generate a brand-new `DB_PASSWORD`
for the server** — don't reuse a password that's ever been typed into a shared/logged
session.

**Database**: don't bake a custom Postgres image, and don't `pg_dump`/restore either —
both add moving parts for no benefit, since the metadata table is a few dozen rows. Let
`postgis/postgis` initialize a fresh schema on the server (it already auto-runs
`database/init/01_schema.sql` via the `docker-entrypoint-initdb.d` mount — unchanged),
then populate it by re-running the existing registration step against the transferred
files. This reuses the one already-correct source of truth (`register_layers.py`)
instead of adding a second DB-population path that can drift from the schema.

**Raster data (~11GB today, will grow)**: don't bake this into a Docker image — image
layers are the wrong transport for large, frequently-changing binary data; every change
would mean rebuilding and re-shipping an 11GB+ image with no incremental transfer. Use
`rsync` over SSH instead: resumable, and — importantly — **incremental**, so re-running
it after the real dataset replaces the trial data only transfers what changed.

**Repeatable workflow** (this is the actual point, since trial data will be replaced by
the real dataset later and this needs to happen again without re-deriving a process):

1. Locally: run the existing pipeline (`setup_layers.py`) to produce
   `data/data_files/{Raster,Optimized_Raster}/` and register everything into your local
   Postgres — unchanged from today's workflow.
2. Transfer to the server, same relative path:
   ```bash
   rsync -avz --progress --partial data/data_files/ user@SERVER_IP:~/qgis-app/data/data_files/
   ```
3. On the server, populate the DB from what you just transferred — fast, since it's only
   INSERTs/metadata reads, not re-downloading or re-optimizing:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     run --rm data-loader python setup_layers.py --skip-download --skip-optimize --only-register
   ```
4. When the real dataset arrives (or changes again): redo step 1 locally, re-run the
   same `rsync` command (only new/changed files transfer), then re-run step 3's command.
   Same three commands every time.

This is also the answer to "build images on the server vs. bake data in": **build the
app images on the server from the git-cloned source** (`docker compose build`, no
registry needed), and **sync the raster data separately via `rsync`** — the 11GB payload
never goes inside an image.

---

## Part C — Step-by-step runbook (first deploy of this app)

1. **Server hardening basics** (Ubuntu/Debian), once per server:
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   sudo ufw allow 22/tcp
   sudo ufw enable
   sudo apt install -y fail2ban
   sudo systemctl enable --now fail2ban
   ```
   Confirm Docker is the official Engine, not the Ubuntu `snap` package (a known source
   of permission/stop issues, flagged in this repo's own README troubleshooting
   section).
2. **Clone the repo**:
   ```bash
   git clone https://github.com/vijesh93/QGiS-Application.git ~/qgis-app
   cd ~/qgis-app
   ```
3. **Create `.env`** from `.env.example`, filling in a fresh `DB_PASSWORD` /
   URL-encoded `DB_PASSWORD_URL`, and:
   ```env
   PUBLIC_APP_URL=http://SERVER_IP:8081
   APP_GATEWAY_PORT=9101
   ```
4. **Open this app's public port** and **build + start the stack**:
   ```bash
   sudo ufw allow 8081/tcp
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
   docker compose ps   # confirm db/redis/raster-server/backend/gateway are healthy
   ```
5. **Sync raster data and register it** — Part B, steps 2–3 above.
6. **Install the host nginx block** for this app:
   ```bash
   sudo cp deploy/host-nginx-app.conf.example /etc/nginx/sites-available/qgis-app.conf
   # edit it: APP_PUBLIC_PORT -> 8081, APP_GATEWAY_PORT -> 9101
   sudo ln -s /etc/nginx/sites-available/qgis-app.conf /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
7. **Verify**: open `http://SERVER_IP:8081/` — the map loads, `/api/v1/layers` responds,
   a tile request through `/titiler/...` renders. Run `sudo ufw status` and
   `ss -tulpn` and confirm only `22` and `8081` are reachable — not `9101`, not the
   backend/db/raster-server ports.

---

## Launching another, unrelated app on this same server

This is the part of the design meant to make the *next* app cheap to add. Assuming the
new app is also a Docker Compose project with its own single "entry" container/port
(it doesn't have to use this exact nginx-gateway pattern, but it's a good default to
reuse):

1. Put its code in its own directory on the server (e.g. `~/other-app/`), independent of
   this repo — a completely separate `docker compose` project.
2. Give it its own `.env` with its own unused ports: a public port (e.g. `8082`) and,
   if it follows the same gateway pattern, its own internal `127.0.0.1` port (e.g.
   `9102`). Keep a short running note somewhere (even a `PORTS.md` on the server) of
   which app owns which port/name — the only real bookkeeping this pattern requires.
3. `docker compose up --build -d` that app, exactly as in Part C step 4, just pointed at
   its own compose files.
4. Copy `deploy/host-nginx-app.conf.example` again, this time as e.g.
   `/etc/nginx/sites-available/other-app.conf`, with `APP_PUBLIC_PORT=8082` and its own
   `proxy_pass` target. Symlink into `sites-enabled/`, `nginx -t`, reload.
5. `sudo ufw allow 8082/tcp`.

Nothing about *this* app (ports, containers, nginx config) needs to change when you do
this — that's the point of giving each app its own port and its own host-nginx block
instead of sharing one.

---

## Going from IP+HTTP to a domain + HTTPS (per app, whenever that app gets a domain)

1. Point a DNS A record for e.g. `gis.yourdomain.com` at the server's IP.
2. Edit that app's file in `/etc/nginx/sites-available/`: change
   `listen 8081; server_name _;` to `listen 80; server_name gis.yourdomain.com;` — the
   `proxy_pass http://127.0.0.1:9101;` line does not change; Docker is untouched.
3. One-time per server: `sudo apt install certbot python3-certbot-nginx`.
4. `sudo certbot --nginx -d gis.yourdomain.com` — certbot edits the block to add the
   443/TLS listener and an HTTP→HTTPS redirect, and sets up renewal via a systemd timer.
5. Update that app's `.env`: `PUBLIC_APP_URL=https://gis.yourdomain.com`, then rebuild
   just the services whose env changed:
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d backend gateway
   ```
   (`gateway` needs rebuilding because `VITE_API_URL`/`VITE_TITILER_URL` stay the same
   relative paths either way — only `backend`'s `CORS_ORIGINS` actually changes — but
   rebuilding both is cheap and keeps things simple.)
6. Once confirmed working, optionally close the old numeric port:
   `sudo ufw delete allow 8081/tcp`.

---

## Backups & maintenance

- Cron a nightly `pg_dump` of the `geoportal` DB to a file outside the containers (small
  — it's metadata only), with rotation (keep N days). This is for disaster recovery, not
  the normal data-update path (that's the `rsync` + `--only-register` workflow above).
- `data/data_files` is regenerable from the pipeline (and lives outside git already), so
  it's lower backup priority than the DB — but back it up too if re-downloading/
  re-optimizing from scratch would be slow.
- Manual or scheduled `docker compose pull && docker compose up -d` to pick up base-image
  updates (`postgis`, `redis`, `titiler`, `nginx:alpine`).

## Verification checklist

- `docker compose -f docker-compose.yml -f docker-compose.prod.yml config` validates
  cleanly.
- The dev stack (`-f docker-compose.yml -f docker-compose.dev.yml`) still works
  unchanged after the base-file port move — check this, since dev is used daily.
- On the server: only `gateway`'s `127.0.0.1` port and host nginx's public port are
  involved; `/`, `/api/v1/layers`, and a sample `/titiler/...` tile all load through the
  single public port.
- After a raster re-sync + `--only-register` run: new/changed layers appear without
  re-running download/optimize.
- `sudo ufw status` / `ss -tulpn` show no unintended open ports after each new app is
  added.
