# Prod migration: `band_labels` column (mean-band removal + fast-register)

## What changed and why

`data/register_layers.py` now writes an optional `band_labels TEXT[]` column on `layer_metadata`, alongside the existing `band_start_date`/`band_date_step_days`. It's populated for a multi-band layer whose bands don't follow the `<var>_<year>_<day-of-year>` date convention but still each carry a real description — e.g. a 3-band prediction raster described as `near`/`medium`/`far` rather than literal dates. See `database/init/01_schema.sql` and `backend/models/db_models/db_model.py` for the column definition, and `frontend/src/components/ActiveLayersLegend.jsx`'s `formatBandLabel()` for how it's displayed.

This came bundled with two other changes in the same release that prod needs to pick up together:
- The optimizer no longer prepends a synthetic "mean" band — `data/raster_utils.py`. Any already-optimized file on the server will be detected as stale (band count mismatch) and automatically rebuilt the next time the optimize step runs against its raw source.
- `data/register_layers.py` gained a `--fast` flag (and `setup_layers.py` a `--fast-register` passthrough) that trusts a `<stem>.meta.json` sidecar instead of recomputing metadata — see "Fast register" below.

There is **no migration tool** (Alembic or similar) wired into this repo. `database/init/01_schema.sql` only runs once, against a brand-new, empty Postgres data volume (via `docker-entrypoint-initdb.d`) — it does **not** retroactively alter a database that's already running. To cover exactly this gap, `register_layers.py` now self-applies this specific additive change on every run (see `ensure_schema()`), so **in the common case you don't need to do anything manual** — just redeploy and run registration as usual. The manual steps below are the fallback for when that self-apply can't run (e.g. the prod app's DB role has no `ALTER TABLE` rights by design).

## Option A (default): let `register_layers.py` apply it automatically

`register_layers.py` calls `ensure_schema(cur)` at the start of every run (slow or `--fast`), which executes:
```sql
ALTER TABLE layer_metadata ADD COLUMN IF NOT EXISTS band_labels TEXT[];
```
This is a no-op if the column already exists, so it's safe to run every time, on every environment. On prod, this means your normal deploy/registration step is enough:

```bash
# normal (first time after this release, or whenever raw rasters changed) —
# recomputes metadata and also writes the sidecar files for future --fast runs:
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm data-loader python setup_layers.py --skip-download --skip-optimize --only-register

# OR, once sidecars already exist from a prior normal run (faster — no
# gdalinfo/rasterio work on the server at all):
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  run --rm data-loader python setup_layers.py --skip-download --skip-optimize --only-register --fast-register
```

If this succeeds, you're done — skip Option B entirely. You'll see `ALTER TABLE` silently succeed (or no-op) before the per-layer processing starts; no separate output line, since it's not expected to fail in the common case.

## Option B (fallback): apply the column manually

Only needed if Option A's `ensure_schema()` call fails — this happens when the Postgres role the app connects as (`DATABASE_URL`'s user) doesn't have `ALTER TABLE` privilege on `layer_metadata`, which is a deliberate hardening choice on some prod setups (DDL rights intentionally separated from the app's day-to-day DML role). `register_layers.py` will raise a clear error telling you to do this; the steps below are that error, spelled out.

1. **Find the DB container name and the role to connect as.** The role is whatever `POSTGRES_USER` is set to for that environment (it was `ffsadmin` in dev — check prod's `.env` or compose override, don't assume `postgres`):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml ps db
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db env | grep POSTGRES_USER
   ```

2. **Connect and run the `ALTER TABLE`** (idempotent — safe to re-run; `IF NOT EXISTS` means it no-ops if already applied):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db \
     psql -U <POSTGRES_USER> -d <POSTGRES_DB> \
     -c "ALTER TABLE layer_metadata ADD COLUMN IF NOT EXISTS band_labels TEXT[];"
   ```
   (`<POSTGRES_DB>` is usually `geoportal` — confirm from the same `env | grep POSTGRES` output as step 1.)

3. **Verify the column landed:**
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml exec db \
     psql -U <POSTGRES_USER> -d <POSTGRES_DB> -c "\d layer_metadata"
   ```
   Confirm `band_labels | text[]` appears in the column list.

4. **Now run registration as normal** (same commands as Option A above — `ensure_schema()` will no-op cleanly against the column you just added by hand):
   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml \
     run --rm data-loader python setup_layers.py --skip-download --skip-optimize --only-register --fast-register
   ```

## Verifying the deploy worked end to end

1. **Schema:** `\d layer_metadata` (as in Option B step 3) shows `band_labels text[]`.
2. **Mean-band rebuild:** check the optimize step's output for any multi-band layer — it should log a rebuild (not "already optimized, skipping") the first time it runs post-deploy, since every pre-existing multi-band COG now has a band-count mismatch (`N+1` old vs. `N` new) and is correctly flagged stale.
3. **Registration:** `SELECT slug, band_count, band_start_date, band_labels FROM layer_metadata WHERE band_count > 1;` — date-sequence layers should show `band_start_date` set and `band_labels` NULL; qualitative layers (e.g. near/medium/far) should show the reverse.
4. **API:** `curl <backend>/api/v1/layers/?category=<cat>` and confirm `band_labels` appears in the JSON for the relevant layer(s).
5. **Frontend:** open the app, activate a qualitative multi-band layer, and confirm the time slider shows the real labels (e.g. "near"/"medium"/"far") instead of "Day 1 of 3".

## Rolling back

The column is purely additive and nothing reads it unless populated, so there's no destructive rollback needed. If you must remove it (e.g. reverting this release entirely):
```sql
ALTER TABLE layer_metadata DROP COLUMN IF EXISTS band_labels;
```
Only do this after confirming the reverted code no longer references the column (`backend/models/db_models/db_model.py`, `backend/repositories/layer_repo.py`, `data/register_layers.py`) — dropping it while a running app still selects/inserts it will break every `layers` API call and every registration run.
