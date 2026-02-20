from sqlmodel import SQLModel
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime


# DTOs / API schemas
class LayerCreate(SQLModel):    # Most probably not needed, as read only application
    name: str
    display_name: str
    category: Optional[str] = None
    geometry_type: Optional[str] = None
    is_visible_by_default: Optional[bool] = False


class LayerRead(SQLModel):
    id: int
    name: str
    display_name: str
    category: Optional[str]
    geometry_type: Optional[str]
    is_visible_by_default: bool


class LayerBase(BaseModel):
    name: str = Field(..., description="The internal table name in PostGIS")
    display_name: str = Field(..., description="User-friendly label")
    category: Optional[str] = None
    geometry_type: str = Field("RASTER", description="RASTER or VECTOR")


class LayerRead(LayerBase):
    id: int
    is_visible_by_default: bool
    created_at: datetime
    # We include the tile URL so the frontend doesn't have to guess
    tile_url: str = Field(..., description="The pg_tileserv URL for this layer")
    
    class Config:
        from_attributes = True


class CategorySummary(BaseModel):
    category: str
    layer_count: int