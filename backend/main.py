from fastapi import FastAPI
from typing import List
from models.db_models.db_model import Layer

from db import get_session, engine

app = FastAPI(title="Baden-Württemberg GIS API")

# Include routers (import here to avoid circular imports)
from api.v1 import layers as layers_router
app.include_router(layers_router.router, prefix="/api/v1")


@app.get("/")
def root():
    return {"message": "GIS Backend is running. Go to /docs for API info."}