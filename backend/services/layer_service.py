"""
Docstring for backend.services.layer_service:

This script implements the layer related business logic, i.e., the python controler is redirected here from the API entry point!
"""

from sqlmodel import Session 
from repositories.layer_repo import LayerRepository
from schemas.layer import CategorySummary, LayerRead
from typing import List, Optional


class LayerService:
    def __init__(self, session: Session):
        self.repo = LayerRepository(session)

    def list_categories(self):
        results = self.repo.get_categories()
        # Explicitly map the result (category, count) to the schema
        return [CategorySummary(category=r[0], count=r[1]) for r in results]

    def list_categories(self):
        results = self.repo.get_categories()
        # Explicitly map the DB tuple to the Pydantic schema
        return [CategorySummary(category=r[0], layer_count=r[1]) for r in results]

    def get_category_layers(self, category: str) -> List[LayerRead]:
        results = self.repo.get_by_category(category)
        # Results are rows from our '_get_base_select'
        # LayerRead.model_validate will handle the conversion automatically
        return [LayerRead.model_validate(r) for r in results]

    def get_by_slug(self, slug: str) -> Optional[LayerRead]:
        result = self.repo.get_by_slug(slug)    # Single element and not a list

        if result is None:
            return None

        # LayerRead.model_validate will handle the conversion automatically
        return LayerRead.model_validate(result)
