Backend Architecture
Overview

This backend follows a layered architecture inspired by Clean Architecture principles. The goal of this structure is to ensure:

Clear separation of concerns

Maintainability

Scalability

Testability

Safe extension for future features

The system is designed to manage raster layer metadata, coordinate with COG-optimized raster files, and integrate with a raster rendering service (e.g., TiTiler).

The backend does not render raster pixels directly. Instead, it:

Stores raster metadata in the database

Manages layer configuration

Exposes REST endpoints

Provides raster paths to the tile server

Enforces business rules

High-Level Architecture
Client (Frontend Map App)
        ↓ HTTP
FastAPI Application (main.py)
        ↓
API Layer (api/v1/)
        ↓
Service Layer (services/)
        ↓
Repository Layer (repositories/)
        ↓
Database Models (models/db_models/)
        ↓
Database (PostgreSQL / PostGIS)

Raster tiles are rendered separately by a raster service (e.g., TiTiler), which reads COG files from disk.

Directory Structure and Responsibilities
1. main.py
Role: Application Entry Point

Responsibilities:

Creates the FastAPI app instance

Registers routers

Configures middleware

Initializes the database connection

This file is responsible for bootstrapping the application.

It should NOT contain:

Business logic

Database queries

Feature-specific implementations

2. api/v1/

Example:

api/v1/layers.py
Role: API Layer (Controllers)

Responsibilities:

Defines HTTP routes

Validates input via schemas

Calls the service layer

Returns formatted responses

This layer handles HTTP concerns only.

It should NOT contain:

SQL queries

Business logic

Complex processing

Think of this layer as the translation layer between HTTP and internal logic.

3. services/

Example:

services/layer_service.py
Role: Business Logic Layer

Responsibilities:

Implements domain rules

Orchestrates repository calls

Combines filesystem and database logic

Applies validation rules

Generates tile URLs

Controls layer activation logic

This is the “brain” of the application.

It should NOT contain:

Raw SQL

HTTP request handling

This layer is where most new features should be implemented.

4. repositories/

Example:

repositories/layer_repo.py
Role: Data Access Layer

Responsibilities:

Communicates directly with the database

Performs CRUD operations

Executes ORM or raw SQL queries

Returns database objects

This layer should be thin and focused.

It should NOT contain:

Business rules

HTTP logic

Filesystem operations

Think of it as a translator between Python objects and database tables.

5. models/db_models/

Example:

models/db_models/db_model.py
Role: Database Structure Definition

Responsibilities:

Defines SQLAlchemy models

Maps Python classes to database tables

Defines relationships between tables

Reflects the database schema

This layer describes how data is stored.

It should NOT contain:

Business logic

API logic

6. schemas/

Example:

schemas/layer.py
Role: Data Validation & Serialization

Responsibilities:

Define request models

Define response models

Validate input data

Control output structure

This ensures:

Type safety

Clean API responses

No leakage of internal database fields

Schemas act as the contract between backend and frontend.

7. db.py
Role: Database Session Management

Responsibilities:

Create SQLAlchemy engine

Provide session factory

Manage connections

Configure pooling

All repositories depend on this module for database access.

8. utils/

Example:

utils/validation.py
Role: Shared Utility Logic

Responsibilities:

File validation

Raster path checks

Reusable helpers

Common validation logic

This prevents duplication across services.

Data Flow Example
Example: Fetch All Layers
Step 1 — Client Request
GET /api/v1/layers
Step 2 — API Layer

Route defined in api/v1/layers.py

Validates request

Calls service method

Step 3 — Service Layer

Applies business rules

Calls repository

Step 4 — Repository Layer

Queries database

Returns layer records

Step 5 — Service Layer

Processes records

Adds tile URLs if needed

Returns structured result

Step 6 — API Layer

Serializes response via schema

Sends JSON to client

Raster Integration Architecture

The backend manages raster metadata, while tile rendering is delegated to a raster service.

Frontend
   ↓
FastAPI Backend (metadata management)
   ↓
TiTiler (COG rendering)
   ↓
COG files on disk

The backend:

Stores raster file paths

Validates metadata

Provides tile endpoint URLs

TiTiler:

Reads COG files

Generates map tiles dynamically

Architectural Principles Used
1. Separation of Concerns

Each layer has a clearly defined responsibility.

2. Single Responsibility Principle

Each module focuses on one task.

3. Dependency Direction

Dependencies flow inward:

API → Service → Repository → Model

Never the opposite direction.

4. Extensibility

New features can be added without heavily modifying existing layers.

How to Extend the System
Adding a New Field to Layers

Update db_model.py

Update the corresponding schema

Update repository queries

Update service logic if needed

Update API response

Adding a New Feature (Example: Layer Categories)

Add column in database model

Create repository filter method

Add service-level logic

Add new API endpoint

Update schema

Adding Raster Upload Support

Add upload endpoint in API

In service:

Save file

Trigger COG optimization

Create database record

In repository:

Insert new layer

Return structured response

Adding Caching

Caching logic should be added in the service layer.

Possible options:

In-memory caching

Redis

Background refresh

Adding Authentication

API layer: extract user

Service layer: enforce permission rules

Repository layer: unchanged

Why This Architecture Works

Clean structure

Easy debugging

Scalable for large raster systems

Safe for adding new features

Clear ownership of logic

Supports background processing

Compatible with microservice evolution

Summary

This backend is a Raster Layer Management System.

It:

Stores raster metadata

Exposes REST endpoints

Delegates rendering to a tile server

Maintains clean separation of logic layers

The architecture is production-ready and designed for future growth, including:

Async processing

Raster uploads

Role-based access

Caching

Large-scale raster management