from sqlmodel import SQLModel
from typing import Optional


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
