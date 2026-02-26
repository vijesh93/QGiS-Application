from sqlmodel import SQLModel
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
import json


# DTOs / API schemas
class LayerRead(BaseModel):
    # Use ConfigDict for Pydantic v2
    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True  # This stops the "Any" crash
    )

    id: int
    slug: str
    display_name: str
    category: str
    layer_type: str
    file_path: Optional[str]
    extent: Optional[Any] = None

    @field_validator("extent", mode="before")
    @classmethod
    def parse_geojson(cls, v: Any) -> Any:
        # If the database sent a string (from ST_AsGeoJSON), 
        # convert it to a real Python dictionary/JSON object.
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
    

class CategorySummary(BaseModel):
    category: str
    layer_count: int