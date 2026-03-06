from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlmodel import Session, select
from db import get_session
from services.layer_service import LayerService
from models.db_models.db_model import Layer as LayerModel
from schemas.layer import LayerRead, CategorySummary, RasterCount


router = APIRouter(prefix="/layers", tags=["Layers"])


@router.get("/categories", response_model=List[CategorySummary])
def get_categories(session: Session = Depends(get_session)):
    """Fetch all unique categories for the sidebar accordion."""
    return LayerService(session).list_categories()

@router.get("/rasters/count", response_model=RasterCount)
def get_raster_count(session: Session = Depends(get_session)):
    """Fetch total number of rasters in the database and return as json file"""
    return LayerService(session).get_raster_count()

@router.get("/", response_model=List[LayerRead])
def get_layers(
    category: str = Query(..., description="Filter layers by category"), 
    session: Session = Depends(get_session)
):
    """Fetch layers within a specific category."""
    layers = LayerService(session).get_category_layers(category)
    if not layers:
        raise HTTPException(status_code=404, detail="No layers found in this category")
    return layers


@router.get("/{slug}", response_model=LayerRead)
def get_layer_details(slug: str, session: Session = Depends(get_session)):
    """Fetch metadata for a single specific layer."""
    layer = LayerService(session).get_by_slug(slug)
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return layer


"""
from repositories.example_safe_querry import get_features_geojson
@router.get("/layers", response_model=List[LayerRead])
def list_layers(session: Session = Depends(get_session)):
    stmt = select(LayerModel)
    results = session.exec(stmt).all()
    return results


@router.get("/layers/{layer_name}", response_model=LayerRead)
def get_layer(layer_name: str, session: Session = Depends(get_session)):
    stmt = select(LayerModel).where(LayerModel.name == layer_name)
    layer = session.exec(stmt).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")
    return layer


@router.get("/layers/{layer_name}/features")
def get_layer_features(
    layer_name: str,
    bbox: Optional[str] = Query(None, description="xmin,ymin,xmax,ymax"),
    limit: int = Query(100, lte=1000),
    session: Session = Depends(get_session),
):
    # Validate the layer exists (whitelist table names)
    stmt = select(LayerModel).where(LayerModel.name == layer_name)
    layer = session.exec(stmt).first()
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found")

    # Parse bbox param
    bbox_tuple = None
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError
            bbox_tuple = (parts[0], parts[1], parts[2], parts[3])
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Use xmin,ymin,xmax,ymax")

    # Use the safe feature query (table_name already validated)
    geojson = get_features_geojson(session, layer_name, bbox=bbox_tuple, limit=limit)
    return geojson
"""

# Modify based on the following code:
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from db import get_db
from services.layer_service import LayerService
from schemas.layer import LayerRead, CategorySummary
from typing import List


router = APIRouter(prefix="/layers", tags=["layers"])

@router.get("/categories", response_model=List[CategorySummary])
def get_categories(db: Session = Depends(get_db)):
    # Step 1: Frontend calls this to build the sidebar folders.
    return LayerService(db).list_categories()

@router.get("/", response_model=List[LayerRead])
def get_layers(
    category: str = Query(..., description="Category to filter by"), 
    db: Session = Depends(get_db)
):
    # Step 2: Frontend calls this when a folder is opened
    return LayerService(db).get_category_layers(category)
"""