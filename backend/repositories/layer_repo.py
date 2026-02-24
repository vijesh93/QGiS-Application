# This handles the raw SQL communication.

from sqlmodel import Session, select, func
from models.db_models.db_model import Layer
from typing import List


# DAO
class LayerRepository:
    def __init__(self, session: Session):
        self.session = session
    
    def get_categories(self):
        # Equivalent to SELECT category, count(*) GROUP BY category
        statement = select(Layer.category, func.count(Layer.id)).group_by(Layer.category)
        return self.session.exec(statement).all()

    def get_by_category(self, category: str) -> List[Layer]:
        statement = select(Layer).where(Layer.category == category).where(Layer.is_active == True)
        return self.session.exec(statement).all()

    def get_by_slug(self, slug: str) -> Layer:
        statement = select(Layer).where(Layer.slug == slug)
        return self.session.exec(statement).first()

    def get_by_display_name(self, name: str) -> Layer | None:
        stmt = select(Layer).where(Layer.display_name == name)
        return self.session.exec(stmt).first()


    """
    # Might have to add this in future, but needs db model modification
    def list_active(self):
        stmt = select(Layer).where(Layer.is_visible_by_default == True)
        return self.session.exec(stmt).all()
    """
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