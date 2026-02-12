from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel


class Layer(SQLModel, table=True):
    __tablename__ = "layer_metadata"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    display_name: str
    category: Optional[str] = None
    geometry_type: Optional[str] = None
    is_visible_by_default: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

# This model can later be extended for your GenAI features
# e.g., adding a 'description_vector' column for semantic search