from sqlmodel import SQLModel, Field, Column
from typing import Optional, Any
from datetime import date
from geoalchemy2 import Geometry
import json


class Layer(SQLModel, table=True):
    __tablename__ = "layer_metadata"
    
    # Add model_config here too if the error persists in the DB model
    model_config = {"arbitrary_types_allowed": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    display_name: str
    category: str = Field(index=True)
    layer_type: str
    file_path: Optional[str] = None
    is_active: bool = Field(default=True)

    # Geometry column
    bbox: Optional[Any] = Field(sa_column=Column(Geometry("POLYGON", srid=4326)))

    # Real (nodata-excluded) band min/max, used as the TiTiler rescale window
    # so each layer gets its own color stretch instead of a hardcoded one.
    min_value: Optional[float] = None
    max_value: Optional[float] = None

    # Time-series metadata: band 1 is a synthetic "mean" band when band_count > 1.
    # band_start_date/band_date_step_days describe bands 2..band_count; NULL means
    # no parseable per-band date convention was found for this raster.
    band_count: int = Field(default=1)
    band_start_date: Optional[date] = None
    band_date_step_days: Optional[int] = None

# This model can later be extended for GenAI features
# e.g., adding a 'description_vector' column for semantic search
