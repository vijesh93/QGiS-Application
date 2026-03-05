# Backend Architecture — GIS Raster Hosting Platform

## Overview

This backend powers a web platform for hosting and displaying GIS raster layers on OpenStreetMap. It is built with **FastAPI** and follows **Clean Architecture** principles to ensure clear separation of concerns, maintainability, and scalability.

The system manages metadata for ~500 raster layers, coordinates with COG-optimized raster files on disk, and integrates with **TiTiler** for tile rendering.

> **Key principle:** The backend does not render raster pixels directly. It manages metadata, enforces business rules, and provides tile endpoints — rendering is delegated entirely to TiTiler.

---

## System Context

```
Client (Frontend Map App — OpenStreetMap)
        │
        │ HTTP (REST)
        ▼
FastAPI Backend
  ├── Manages raster metadata
  ├── Exposes REST endpoints
  └── Provides tile URLs
        │
        ▼
TiTiler (Tile Rendering Service)
  └── Reads COG files from disk
        │
        ▼
COG Files on Disk (~500 rasters)
```

---

## Layered Architecture

```
api/v1/             ← HTTP routes, input validation, response serialization
    │
services/           ← Business logic, orchestration, tile URL generation
    │
repositories/       ← Database CRUD, ORM queries
    │
models/db_models/   ← SQLAlchemy table definitions
    │
PostgreSQL/PostGIS  ← Persistent storage
```

Dependencies flow **inward only**. The API layer never imports from repositories directly, and no layer below the service layer knows about HTTP.

---

## Directory Structure

```
.
├── main.py                     # App entry point, router registration, middleware
├── db.py                       # SQLAlchemy engine, session factory
├── api/
│   └── v1/
│       └── layers.py           # Route definitions for raster layer endpoints
├── services/
│   └── layer_service.py        # Business logic, tile URL generation, orchestration
├── repositories/
│   └── layer_repo.py           # Database queries (CRUD)
├── models/
│   └── db_models/
│       └── db_model.py         # SQLAlchemy ORM models
├── schemas/
│   └── layer.py                # Pydantic request/response schemas
└── utils/
    └── validation.py           # Shared helpers (file checks, raster path validation)
```

---

## Module Responsibilities

### `main.py` — Application Entry Point

Bootstraps the FastAPI application. Registers routers, configures middleware, and initializes the database connection.

**Must not contain:** business logic, database queries, or feature-specific code.

---

### `api/v1/` — API Layer (Controllers)

Defines HTTP routes. Validates incoming requests via Pydantic schemas and delegates all logic to the service layer. Returns serialized JSON responses.

**Must not contain:** SQL queries, business logic, or complex processing.

---

### `services/` — Business Logic Layer

The core of the application. Implements domain rules, orchestrates repository calls, combines filesystem and database concerns, and generates TiTiler tile URLs.

**Must not contain:** raw SQL, HTTP request handling.

Key responsibilities:
- Layer activation/deactivation logic
- Tile URL generation (e.g., constructing TiTiler endpoints from stored COG paths)
- Coordinating multiple repository calls
- Caching logic (if applicable)
- Permission enforcement (if authentication is added)

---

### `repositories/` — Data Access Layer

Communicates directly with the database. Performs CRUD operations using SQLAlchemy ORM or raw SQL where necessary. Returns database model objects.

**Must not contain:** business rules, HTTP logic, or filesystem operations.

---

### `models/db_models/` — Database Models

SQLAlchemy model definitions that map Python classes to PostgreSQL/PostGIS tables. Defines table structure and relationships.

**Must not contain:** business logic or API logic.

---

### `schemas/` — Pydantic Schemas

Defines the contract between the API and its clients. Controls what fields are accepted in requests and what fields are exposed in responses. Prevents internal database fields from leaking to the frontend.

---

### `db.py` — Database Session Management

Creates the SQLAlchemy engine, session factory, and manages connection pooling. All repositories depend on this module for database access.

---

### `utils/` — Shared Utilities

Reusable helpers used across layers — file existence checks, raster path validation, and other common logic. Prevents duplication across services.

---

## Data Flow Example

### `GET /api/v1/layers` — Fetch All Layers

```
1. Client sends GET /api/v1/layers

2. api/v1/layers.py
   └── Validates request
   └── Calls layer_service.get_all_layers()

3. services/layer_service.py
   └── Applies any business rules (e.g., active layers only)
   └── Calls layer_repo.get_all()

4. repositories/layer_repo.py
   └── Queries PostgreSQL
   └── Returns list of ORM model instances

5. services/layer_service.py
   └── Enriches records (e.g., attaches TiTiler tile URLs)
   └── Returns structured result

6. api/v1/layers.py
   └── Serializes via Pydantic schema
   └── Returns JSON response to client
```

---

## Raster Integration

The backend stores raster file paths and configuration. TiTiler handles all tile rendering.

| Responsibility        | Component       |
|-----------------------|-----------------|
| Raster metadata       | FastAPI backend |
| COG file paths        | FastAPI backend |
| Tile URL generation   | FastAPI backend |
| Pixel rendering       | TiTiler         |
| COG file storage      | Disk            |

Tile URLs follow the pattern:
```
https://<titiler-host>/cog/tiles/{z}/{x}/{y}.png?url=<cog_file_path>
```

These URLs are constructed in the **service layer** and returned to the frontend as part of layer responses.

---

## Architectural Principles

| Principle | Application |
|-----------|-------------|
| Separation of Concerns | Each layer has a single, well-defined responsibility |
| Single Responsibility | Each module focuses on one task |
| Dependency Direction | API → Service → Repository → Model (never reversed) |
| Extensibility | New features can be added to one layer without breaking others |

---

## Extension Guide

### Adding a New Field to Layers
1. Update `models/db_models/db_model.py`
2. Update the corresponding Pydantic schema in `schemas/layer.py`
3. Update `repositories/layer_repo.py` queries if needed
4. Update service logic if the field affects business rules
5. Verify the API response reflects the new field

### Adding a New Feature (e.g., Layer Categories)
1. Add column in `db_model.py`
2. Create a filter/query method in `layer_repo.py`
3. Add business logic in `layer_service.py`
4. Add new endpoint in `api/v1/layers.py`
5. Update schema for request/response

### Adding Raster Upload Support
1. Add upload endpoint in `api/v1/`
2. In `layer_service.py`: save file to disk, trigger COG optimization, create DB record
3. In `layer_repo.py`: insert new layer record, return structured response

### Adding Caching
- Implement in the **service layer** only
- Options: in-memory (`functools.lru_cache`), Redis, or background refresh via APScheduler

### Adding Authentication
- **API layer**: extract user from JWT/session
- **Service layer**: enforce role-based permission rules
- **Repository layer**: unchanged — remains unaware of auth context

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| API framework | FastAPI |
| Database | PostgreSQL + PostGIS |
| ORM | SQLAlchemy |
| Schema validation | Pydantic |
| Raster rendering | TiTiler |
| Raster format | Cloud Optimized GeoTIFF (COG) |
| Raster count | ~500 layers |

---

## Design Goals

- **Production-ready structure** from day one
- **Thin controllers** — HTTP concerns are fully isolated from business logic
- **Testable layers** — services and repositories can be unit tested independently
- **GIS-native** — PostGIS and COG formats are first-class citizens
- **Delegation over duplication** — rendering is owned by TiTiler, not the backend
