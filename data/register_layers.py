"""
This script feeds the COG (optimized) layer meta data to the database.

Supports two modes:
  - Normal (default): does the full per-file work (gdalinfo, rasterio band
    scan, VRT generation), then writes a `<stem>.meta.json` sidecar next to
    each optimized COG caching everything needed to register it again
    without redoing that work.
  - --fast: trusts the sidecar written by a prior normal run (e.g. the local
    run before `rsync`-ing data_files/ to the server) and does nothing but
    read JSON + INSERT — zero gdalinfo/rasterio/subprocess calls. A file
    with a missing or stale sidecar is skipped with a warning, same policy
    as every other per-file skip condition below.

Also self-applies any additive schema changes it depends on (see
ensure_schema()) on every run — there's no migration tool wired into this
repo, so a server DB that was provisioned before a given column existed
gets it added automatically instead of needing a one-off manual ALTER.
"""
import argparse
import csv
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional

import psycopg2
import rasterio

from raster_utils import compute_band_range, generate_band_vrts, is_stale_timeseries_output, parse_band_date_convention

# ── Paths (work inside container AND on host, Windows or Linux) ──────────────
# Script lives at:  data/register_layers.py
# Container maps:   ./data → /app
# So:  __file__ parent = "data/" on host, "/app" in container — same structure.

_SCRIPT_DIR = Path(__file__).resolve().parent   # data/  (host) or /app/ (container)
# _SCRIPT_DIR = Path(os.getcwd()).resolve()

RASTER_DIR        = _SCRIPT_DIR / "data_files" / "Raster"
OPTIMIZED_DIR     = _SCRIPT_DIR / "data_files" / "Optimized_Raster"
UNCATEGORIZED     = "Uncategorized"

# Legacy safety net: skip any orphaned temp file a pre-mean-band-removal
# crashed run may have left behind. Nothing creates these anymore.
_BAND_MEAN_TMP_SUFFIX = ".band_mean_tmp.tif"

_SIDECAR_SUFFIX = ".meta.json"
_SIDECAR_SCHEMA_VERSION = 2  # bumped for subcategory/band_mode; cosmetic marker only
_SIDECAR_MTIME_TOLERANCE_S = 2.0  # rsync/filesystem timestamp rounding slack

_BAND_DISPLAY_MODES_PATH = _SCRIPT_DIR / "band_display_modes.json"
_VALID_BAND_MODES = {"sequence", "distribution"}
_DEFAULT_BAND_MODE = "sequence"

_TIME_HORIZON_RE = re.compile(r"^([A-Za-z]+)_(\d{4}-\d{4})$")
_ABS_DELTA_SUFFIX_RE = re.compile(r"_(abs|delta)$", re.IGNORECASE)

_DISPLAY_NAME_CATALOG_FILENAME = "catalog_portal.csv"

# Path as seen by the raster-server container (its volume mount is also ./data → /data)
def raster_server_path(rel_path: Path) -> str:
    return f"/data/data_files/Optimized_Raster/{rel_path.as_posix()}"


def relative_to_raster(tif: Path) -> Path:
    """Path of a raster relative to RASTER_DIR, e.g. 'aspect/foo.tif'.
    Files sitting directly in RASTER_DIR (no category folder) are bucketed
    under UNCATEGORIZED so every registered layer still has a category."""
    rel = tif.relative_to(RASTER_DIR)
    if len(rel.parts) == 1:
        return Path(UNCATEGORIZED) / rel
    return rel


def relative_to_optimized(cog: Path) -> Path:
    """Path of an optimized COG relative to OPTIMIZED_DIR, e.g. 'aspect/foo.tif'.

    Mirrors relative_to_raster()'s UNCATEGORIZED bucketing, but rooted at
    OPTIMIZED_DIR instead of RASTER_DIR — needed because registration
    discovers layers by scanning OPTIMIZED_DIR directly (see
    register_rasters()), so a COG dropped straight into OPTIMIZED_DIR's root
    with no category subfolder (no raw counterpart required) still lands in
    a category instead of erroring on `rel.parts[0]`."""
    rel = cog.relative_to(OPTIMIZED_DIR)
    if len(rel.parts) == 1:
        return Path(UNCATEGORIZED) / rel
    return rel


def _derive_subcategory(rel_path: Path) -> Optional[str]:
    """Second-level grouping for deeply-nested datasets, e.g. the Variable
    folder ('bio01') in 'SSP2-4.5/bio01/Far_2071-2100/KliMP_..._abs.tif'.
    Generic and NOT gated by band_display_modes.json — any future dataset
    nested more than 2 levels deep under Optimized_Raster/ gets a
    subcategory for free. None for every shallower layer (today's norm),
    which the frontend already treats as "no subgroup" (see useLayers.jsx's
    groupedLayers: `layer.subcategory || ''`).
    """
    return rel_path.parts[1] if len(rel_path.parts) > 2 else None


def _prettify_display_name(rel_path: Path, stem: str) -> str:
    """Best-effort, generic prettifier: when the raster's immediate parent
    folder matches '<Label>_<yyyy>-<yyyy>' (e.g. 'Far_2071-2100') AND the
    filename stem ends in '_abs' or '_delta', builds e.g.
    'Absolute — Far (2071-2100)'. The Absolute/Delta kind leads
    deliberately — sorting layers by display_name (see
    layer_repo.py's get_by_category, which now does exactly that) then
    groups every Absolute layer together and every Delta layer together,
    instead of interleaving them by time horizon.

    Does NOT include the variable name (e.g. 'bio01') — it's already shown
    as the subcategory heading in the sidebar directly above these layers,
    so repeating it in every one of their names would be redundant. The
    pixel-value popup, which shows only one layer's name at a time with no
    sidebar context visible, separately prepends the subcategory there
    instead (see PixelValuePopup.jsx) so two variables sharing the same
    time-horizon/kind still read unambiguously in that context.

    Falls back to today's plain title-cased-stem behavior for every file
    that doesn't match, so no existing (shallower) layer's name changes.
    """
    if len(rel_path.parts) < 2:
        return stem.replace("_", " ").title()

    horizon_match = _TIME_HORIZON_RE.match(rel_path.parts[-2])
    suffix_match = _ABS_DELTA_SUFFIX_RE.search(stem)
    if not (horizon_match and suffix_match):
        return stem.replace("_", " ").title()

    time_label, year_range = horizon_match.group(1), horizon_match.group(2)
    kind = "Absolute" if suffix_match.group(1).lower() == "abs" else "Delta"
    return f"{kind} — {time_label} ({year_range})"


def _load_band_display_modes() -> dict:
    """Maps a layer's top-level category (rel_path.parts[0]) to a band_mode
    override ("distribution"), read from data/band_display_modes.json.
    Categories not listed default to "sequence" — today's time-slider
    behavior — so every existing dataset (aspect, ssp_245, ssp_370,
    Year_2026, ...) is completely unaffected by this file's existence.

    A MISSING manifest is deliberately NOT a hard error: this script must
    keep working on a fresh checkout/server before anyone's added the
    file, and the safe default (everything falls back to "sequence", i.e.
    no behavior change at all) is exactly what should happen in that case.
    A PRESENT-but-malformed manifest (bad JSON, or a value outside
    {"sequence", "distribution"}) IS a hard error — silently ignoring a
    typo'd manifest would be far more confusing than failing loudly, since
    the feature would look "broken" for no visible reason.
    """
    if not _BAND_DISPLAY_MODES_PATH.exists():
        return {}
    try:
        payload = json.loads(_BAND_DISPLAY_MODES_PATH.read_text())
    except json.JSONDecodeError as e:
        raise RuntimeError(f"{_BAND_DISPLAY_MODES_PATH} is not valid JSON: {e}") from e

    modes = payload.get("modes", {})
    for category, mode in modes.items():
        if mode not in _VALID_BAND_MODES:
            raise RuntimeError(
                f"{_BAND_DISPLAY_MODES_PATH}: category '{category}' has invalid "
                f"band_mode '{mode}' — must be one of {sorted(_VALID_BAND_MODES)}."
            )
    return modes


def _load_display_name_catalog() -> dict:
    """Maps a raster's path (relative to RASTER_DIR, POSIX-style — exactly
    what relative_to_optimized()/relative_to_raster() produce) to the
    display name a data drop's own catalog_portal.csv says it should have
    in the frontend. Looked for directly in RASTER_DIR rather than
    anywhere fixed in the repo, since a catalog travels with its own data
    drop — new raw data replaces the whole Raster/ tree wholesale (e.g.
    the Nov 2026 KliMP re-delivery, renamed in as Raster/ alongside the
    previous drop kept at Raster_old/), and a future drop's catalog may
    cover a different set of files entirely.

    Takes priority over _prettify_display_name()'s filename-pattern
    heuristic wherever a path is listed, specifically because filename
    conventions can (and did) change between data drops in ways that
    silently stop matching that heuristic's regexes — e.g. this drop's
    'absolute_2071-2100.tif' no longer ends in '_abs' the way
    'KliMP_bio01_ssp245_far_abs.tif' did. The catalog is authoritative
    when present; the heuristic remains the fallback for any raster path
    the catalog doesn't cover (including a future drop with no catalog at
    all, where this function returns {} and every file falls through to
    it exactly as before this mechanism existed).
    """
    catalog_path = RASTER_DIR / _DISPLAY_NAME_CATALOG_FILENAME
    if not catalog_path.exists():
        return {}
    mapping = {}
    with catalog_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            path = (row.get("path") or "").strip()
            name = (row.get("display_name") or "").strip()
            if path and name:
                mapping[path] = name
    return mapping

# ── DB connection ─────────────────────────────────────────────────────────────
DB_URL = os.getenv("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is not set")


def get_raster_metadata(file_path: Path):
    """Uses gdalinfo CLI to extract the WGS84 bounding box."""
    try:
        result = subprocess.run(
            ["gdalinfo", "-json", str(file_path)],
            capture_output=True, text=True, check=True
        )
        info = json.loads(result.stdout)

        extent = info.get("wgs84Extent", {}).get("coordinates", [[]])[0]
        if not extent:
            return None

        poly_str = ", ".join([f"{c[0]} {c[1]}" for c in extent])
        return {"bbox": f"POLYGON(({poly_str}))"}

    except Exception as e:
        print(f"❌ Error parsing {file_path.name}: {e}")
        return None


def _sidecar_path(optimized: Path) -> Path:
    return optimized.with_name(optimized.stem + _SIDECAR_SUFFIX)


def write_metadata_sidecar(optimized: Path, record: dict) -> None:
    """Writes `<stem>.meta.json` next to `optimized`, caching everything
    `_upsert_layer_metadata` needs plus integrity-check fields, so a later
    `--fast` run can register this exact file without re-running gdalinfo,
    rasterio, or VRT generation. Lives alongside the .tif using the same
    sibling-file convention as `generate_band_vrts`' `_band{n:03d}.vrt`
    files, so it travels with it automatically via `rsync`.
    """
    stat = optimized.stat()
    payload = {
        "schema_version": _SIDECAR_SCHEMA_VERSION,
        "optimized_mtime": stat.st_mtime,
        "optimized_size": stat.st_size,
        "slug": record["slug"],
        "display_name": record["display_name"],
        "category": record["category"],
        "subcategory": record["subcategory"],
        "layer_type": record["layer_type"],
        "file_path": record["file_path"],
        "bbox": record["bbox"],
        "min_value": record["min_value"],
        "max_value": record["max_value"],
        "band_count": record["band_count"],
        "band_start_date": record["band_start_date"].isoformat() if record["band_start_date"] else None,
        "band_date_step_days": record["band_date_step_days"],
        "band_labels": record["band_labels"],
        "band_mode": record["band_mode"],
    }
    _sidecar_path(optimized).write_text(json.dumps(payload, indent=2))


def read_metadata_sidecar(optimized: Path) -> Optional[dict]:
    """Reads back a sidecar written by `write_metadata_sidecar`, or returns
    None if it's missing OR stale relative to `optimized`'s current mtime
    (beyond a small tolerance) or size — e.g. someone replaced the COG
    without re-running the slow path. A None return is the caller's cue to
    skip-and-warn. Deliberately NOT a content hash: that would mean
    re-reading a multi-GB raster, exactly the cost `--fast` exists to avoid.
    """
    path = _sidecar_path(optimized)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    try:
        stat = optimized.stat()
    except OSError:
        return None
    if abs(stat.st_mtime - payload.get("optimized_mtime", -1)) > _SIDECAR_MTIME_TOLERANCE_S:
        return None
    if stat.st_size != payload.get("optimized_size"):
        return None

    band_start_date = date.fromisoformat(payload["band_start_date"]) if payload.get("band_start_date") else None
    return {
        "slug": payload["slug"],
        "display_name": payload["display_name"],
        "category": payload["category"],
        "subcategory": payload.get("subcategory"),
        "layer_type": payload["layer_type"],
        "file_path": payload["file_path"],
        "bbox": payload["bbox"],
        "min_value": payload["min_value"],
        "max_value": payload["max_value"],
        "band_count": payload["band_count"],
        "band_start_date": band_start_date,
        "band_date_step_days": payload["band_date_step_days"],
        "band_labels": payload.get("band_labels"),
        "band_mode": payload.get("band_mode", _DEFAULT_BAND_MODE),
    }


def ensure_schema(cur) -> None:
    """Idempotently brings layer_metadata up to the columns this script
    depends on. There's no migration tool (Alembic or similar) wired into
    this repo, so this stands in for one on every run — deliberately scoped
    to additive, always-safe DDL only (`ADD COLUMN IF NOT EXISTS`), never
    anything that could touch existing data (no renames, type changes, or
    NOT NULL constraints — those need a real migration, reviewed by hand).
    A no-op once the column already exists, so this is cheap to run
    unconditionally, including in --fast mode.

    If the role this script connects as lacks ALTER TABLE rights (e.g. a
    deliberately locked-down prod app role, common when DDL and DML
    privileges are intentionally separated), this fails loudly with the
    equivalent manual command rather than limping on to an INSERT that
    would fail anyway with a less obvious "column does not exist" error.
    """
    statements = [
        "ALTER TABLE layer_metadata ADD COLUMN IF NOT EXISTS band_labels TEXT[];",
        "ALTER TABLE layer_metadata ADD COLUMN IF NOT EXISTS subcategory VARCHAR(100);",
        "ALTER TABLE layer_metadata ADD COLUMN IF NOT EXISTS band_mode VARCHAR(20) NOT NULL DEFAULT 'sequence';",
    ]
    for stmt in statements:
        try:
            cur.execute(stmt)
        except Exception as e:
            raise RuntimeError(
                "Could not auto-apply the layer_metadata schema update. If the DB role this "
                "script connects as doesn't have ALTER TABLE rights, run this once by hand "
                "(e.g. via `docker exec <db-container> psql -U <role> -d <db> -c \"...\"`):\n"
                f"  {stmt}"
            ) from e


def _upsert_layer_metadata(cur, record: dict) -> None:
    """The single INSERT ... ON CONFLICT used by both the slow and fast
    registration paths, so they can never drift into executing two subtly
    different versions of the same SQL.
    """
    query = """
        INSERT INTO layer_metadata (
            slug, display_name, category, subcategory, layer_type, file_path, bbox,
            min_value, max_value, band_count, band_start_date, band_date_step_days,
            band_labels, band_mode
        )
        VALUES (%(slug)s, %(display_name)s, %(category)s, %(subcategory)s, %(layer_type)s, %(file_path)s,
                ST_GeomFromText(%(bbox)s, 4326), %(min_value)s, %(max_value)s, %(band_count)s,
                %(band_start_date)s, %(band_date_step_days)s, %(band_labels)s, %(band_mode)s)
        ON CONFLICT (slug) DO UPDATE SET
            display_name         = EXCLUDED.display_name,
            category              = EXCLUDED.category,
            subcategory           = EXCLUDED.subcategory,
            file_path             = EXCLUDED.file_path,
            bbox                  = EXCLUDED.bbox,
            min_value             = EXCLUDED.min_value,
            max_value             = EXCLUDED.max_value,
            band_count            = EXCLUDED.band_count,
            band_start_date       = EXCLUDED.band_start_date,
            band_date_step_days   = EXCLUDED.band_date_step_days,
            band_labels           = EXCLUDED.band_labels,
            band_mode             = EXCLUDED.band_mode;
    """
    cur.execute(query, record)


def register_rasters(fast: bool = False):
    # Discovery is rooted at OPTIMIZED_DIR, not RASTER_DIR: a layer is
    # registerable once an optimized COG exists for it, whether or not a raw
    # source is still around — including a COG that never had one (dropped
    # in by hand, or whose raw file was deleted/archived after optimizing).
    # The raw file, when present, is consulted below only for the staleness
    # check; it plays no part in finding candidates anymore.
    optimized_files = [
        p for p in OPTIMIZED_DIR.rglob("*.tif")
        if not p.name.endswith(_BAND_MEAN_TMP_SUFFIX)
    ]
    if not optimized_files:
        print(f"⚠️  No .tif files found in {OPTIMIZED_DIR}")
        return

    mode = "FAST (sidecar-only)" if fast else "normal"
    print(f"📂 Found {len(optimized_files)} optimized rasters in Optimized_Raster/ folder (across all category subfolders) — mode: {mode}")
    print(f"   Source:                                 {OPTIMIZED_DIR}")
    print(f"   Raw (staleness check only, if present):  {RASTER_DIR}\n")

    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    ensure_schema(cur)
    conn.commit()

    band_display_modes = _load_band_display_modes()
    display_name_catalog = _load_display_name_catalog()
    success, skipped = 0, 0

    for optimized in optimized_files:
        rel_path = relative_to_optimized(optimized)
        category = rel_path.parts[0]
        print(f"▶ Processing: {rel_path}")

        if fast:
            record = read_metadata_sidecar(optimized)
            if record is None:
                print(f"⚠️  Skipping {rel_path}: no valid metadata sidecar found (missing or stale) — "
                      f"re-run without --fast to (re)generate it.")
                skipped += 1
                continue
            _upsert_layer_metadata(cur, record)
            print(f"✅ Registered (fast): {record['slug']} (category: {record['category']}, "
                  f"subcategory: {record['subcategory']}, range: {record['min_value']}..{record['max_value']}, "
                  f"bands: {record['band_count']}, start: {record['band_start_date']}, "
                  f"step_days: {record['band_date_step_days']}, mode: {record['band_mode']})")
            success += 1
            continue

        # Step 1: Staleness only means something relative to a raw source.
        # No raw file is the normal case for a layer that only ever existed
        # as an optimized COG — registration never does conversion work
        # itself (that's cog_optimizer.py's job, via
        # raster_utils.optimize_to_cog), and with nothing to compare against
        # there's nothing to flag as stale; just register what's on disk
        # as-is.
        raw = RASTER_DIR / rel_path  # hypothetical raw counterpart — may not exist
        if raw.exists():
            if is_stale_timeseries_output(raw, optimized):
                print(f"⚠️  Skipping {rel_path}: optimized file is stale (doesn't match "
                      f"the source's band layout) — re-run the optimize step.")
                skipped += 1
                continue
        else:
            print(f"ℹ️  {rel_path}: no raw source found in {RASTER_DIR} — registering "
                  f"the optimized file as-is (nothing to check staleness against).")

        # Step 2: Extract metadata from the optimized file
        meta = get_raster_metadata(optimized)
        if not meta:
            print(f"⚠️  Skipping {rel_path}: no spatial metadata found.")
            skipped += 1
            continue

        # Step 2b: Real (nodata-excluded) value range across all bands, used
        # for the frontend's per-layer TiTiler rescale instead of a
        # one-size-fits-all default. Scanning every band keeps the color
        # scale stable as a user scrubs between timesteps.
        value_range = compute_band_range(optimized)
        min_value, max_value = value_range if value_range else (None, None)

        # Step 2c: Band/time metadata. Band 1 is now the first real timestep
        # (no synthetic mean band is prepended anymore), so every
        # description is checked against the `<var>_<year>_<day-of-year>`
        # convention. When that convention doesn't match but every band
        # still carries a real (non-empty) description, those descriptions
        # are kept verbatim as band_labels — covers rasters whose bands are
        # a qualitative sequence (e.g. "near"/"medium"/"far" prediction
        # horizons) rather than a literal date series. band_labels stays
        # None when the date convention DID match (date math already labels
        # those bands) or when descriptions are missing/partial (nothing
        # meaningful to show — frontend falls back to generic labeling).
        with rasterio.open(optimized) as ds:
            band_count = ds.count
            descriptions = ds.descriptions
        if band_count > 1:
            band_start_date, band_date_step_days = parse_band_date_convention(list(descriptions))
            band_labels = list(descriptions) if band_start_date is None and all(descriptions) else None
        else:
            band_start_date, band_date_step_days = None, None
            band_labels = None

        # Step 2d: One single-band VRT per band, so the frontend's time
        # slider can request a day's tile without TiTiler warping all
        # `band_count` bands just to serve one — see docs/vrt_explainer.md.
        # No-op for single-band layers; cheap no-op for already-fresh VRTs.
        generate_band_vrts(optimized, band_count)

        # Step 3: Register in database
        # slug is prefixed with category (and subcategory, when present) so
        # identically-named files don't collide on the UNIQUE slug column.
        # subcategory is required here, not optional: some data drops name
        # every file within a category identically across variables (e.g.
        # 'absolute_2071-2100.tif' is the exact same filename for bio01,
        # bio05, bio06, and bio12 under SSP2-4.5/Far_2071-2100/) — category
        # + stem alone would collide across all of them and silently
        # overwrite 3 of every 4 variables via the ON CONFLICT upsert.
        # Built from optimized.stem (not the raw file's) since that's the
        # only filename guaranteed to exist — identical to the raw file's
        # stem in the normal case, by construction of cog_optimizer.py.
        subcategory  = _derive_subcategory(rel_path)
        slug_parts   = [category] + ([subcategory] if subcategory else []) + [optimized.stem]
        slug         = "_".join(slug_parts).lower()
        display_name = (
            display_name_catalog.get(rel_path.as_posix())
            or _prettify_display_name(rel_path, optimized.stem)
        )
        band_mode    = band_display_modes.get(category, _DEFAULT_BAND_MODE)
        server_path  = raster_server_path(rel_path)

        record = {
            "slug": slug,
            "display_name": display_name,
            "category": category,
            "subcategory": subcategory,
            "layer_type": "raster",
            "file_path": server_path,
            "bbox": meta["bbox"],
            "min_value": min_value,
            "max_value": max_value,
            "band_count": band_count,
            "band_start_date": band_start_date,
            "band_date_step_days": band_date_step_days,
            "band_labels": band_labels,
            "band_mode": band_mode,
        }
        _upsert_layer_metadata(cur, record)
        write_metadata_sidecar(optimized, record)
        print(f"✅ Registered: {slug} (category: {category}, subcategory: {subcategory}, "
              f"range: {min_value}..{max_value}, bands: {band_count}, start: {band_start_date}, "
              f"step_days: {band_date_step_days}, labels: {band_labels}, mode: {band_mode})")
        success += 1

    # Step 4: Diagnostic-only pass over RASTER_DIR, purely to preserve the
    # old "not optimized yet" warning. Discovery above starts at
    # OPTIMIZED_DIR, so a raw file with no optimized counterpart is never
    # seen by the main loop at all (unlike before, when it WAS the thing
    # being iterated and got an explicit skip message) — without this, that
    # case would go from "flagged" to silently invisible, which is worse
    # during initial setup or after dropping in new raw rasters. This never
    # registers or un-registers anything; it only prints and counts toward
    # `skipped`. Runs unconditionally (slow or fast mode) — it's a cheap
    # filesystem walk, no gdalinfo/rasterio involved.
    for tif in RASTER_DIR.rglob("*.tif"):
        rel_path = relative_to_raster(tif)
        if not (OPTIMIZED_DIR / rel_path).exists():
            print(f"⚠️  Skipping {rel_path}: not optimized yet — run the optimize "
                  f"step first (cog_optimizer.py, or setup_layers.py without --skip-optimize).")
            skipped += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n🚀 Done! {success} registered, {skipped} skipped.")


def main():
    parser = argparse.ArgumentParser(description="Register optimized COG layers in the database.")
    parser.add_argument(
        "--fast", action="store_true",
        help="Trust cached <stem>.meta.json sidecars instead of recomputing metadata "
             "(gdalinfo/rasterio/VRT generation). Files without a valid, up-to-date "
             "sidecar are skipped with a warning. Intended for the server-side "
             "re-register step after rsync-ing data_files/ that was already "
             "registered locally.",
    )
    args = parser.parse_args()
    register_rasters(fast=args.fast)


if __name__ == "__main__":
    main()
