from sqlmodel import SQLModel, Field, Column
from typing import Optional, Any
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

# This model can later be extended for GenAI features
# e.g., adding a 'description_vector' column for semantic search
