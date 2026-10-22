from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String
from sqlalchemy.dialects.postgresql import ARRAY
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

    # Time-series metadata: when band_count > 1, bands 1..band_count are real
    # timesteps/values in source order (no synthetic band is added). NULL
    # band_start_date/band_date_step_days means no parseable per-band date
    # convention was found; band_labels carries raw per-band descriptions
    # instead when the bands are a qualitative (non-date) sequence.
    band_count: int = Field(default=1)
    band_start_date: Optional[date] = None
    band_date_step_days: Optional[int] = None
    band_labels: Optional[list[str]] = Field(default=None, sa_column=Column(ARRAY(String)))

# This model can later be extended for GenAI features
# e.g., adding a 'description_vector' column for semantic search
