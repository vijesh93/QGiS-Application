import os

from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import SQLModel
from db import engine
from fastapi.middleware.cors import CORSMiddleware

# Import the router
from api.v1.layers import router as layers_router


# Allowed origins (Frontend URL). In production this is set via the CORS_ORIGINS
# env var (comma-separated); falls back to the local dev origins when unset so
# local docker-compose.dev.yml usage is unaffected.
_default_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]
_env_origins = os.getenv("CORS_ORIGINS")
origins = (
    [origin.strip() for origin in _env_origins.split(",") if origin.strip()]
    if _env_origins
    else _default_origins
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This runs when the app starts
    # SQLModel.metadata.create_all(engine) # Optional: if you want to create tables automatically
    yield
    # This runs when the app stops

app = FastAPI(
    title="Baden-Württemberg GIS API",
    description="Backend for serving optimized Raster and Vector layers",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows GET, POST, etc.
    allow_headers=["*"],
)

# Prefix Strategy: 
# We include the router here with the versioning prefix.
# Inside api/v1/layers.py, the router should have prefix="/layers"
app.include_router(layers_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
def root():
    return {
        "status": "online",
        "documentation": "/docs",
        "message": "Baden-Württemberg GIS API is operational"
    }
