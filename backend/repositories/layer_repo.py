# This handles the raw SQL communication.

from sqlmodel import Session, select
from backend.models.db_models.db_model import Layer


# DAO
class LayerRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_name(self, name: str) -> Layer | None:
        stmt = select(Layer).where(Layer.name == name)
        return self.session.exec(stmt).first()

    def list_active(self):
        stmt = select(Layer).where(Layer.is_visible_by_default == True)
        return self.session.exec(stmt).all()

# Reference code to integrate: 
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.db_models.db_model import LayerMetadata  # Assuming this is SQLAlchemy model
from typing import List, Type

class LayerRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_layers_by_category(self, category: str) -> List[LayerMetadata]:
        # Fetches all layers belonging to a specific category.
        return self.db.query(LayerMetadata).filter(
            LayerMetadata.category == category
        ).all()

    def get_all_categories(self) -> List[dict]:
        # Returns a list of unique categories and count of layers in each.
        results = self.db.query(
            LayerMetadata.category, 
            func.count(LayerMetadata.id)
        ).group_by(LayerMetadata.category).all()
        
        return [{"category": r[0], "layer_count": r[1]} for r in results]
"""