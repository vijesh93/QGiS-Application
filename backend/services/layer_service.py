"""
Docstring for backend.services.layer_service:

This script implements the layer related business logic, i.e., the python controler is redirected here from the API entry point!
"""

from sqlmodel import Session 
from repositories.layer_repo import LayerRepository
from schemas.layer import CategorySummary


class LayerService:
    def __init__(self, session: Session):
        self.repo = LayerRepository(session)

    def list_categories(self):
        results = self.repo.get_categories()
        return [CategorySummary(category=r[0], count=r[1]) for r in results]

    def list_categories(self):
        results = self.repo.get_categories()
        # Explicitly map the DB tuple to the Pydantic schema
        return [CategorySummary(category=r[0], layer_count=r[1]) for r in results]

    def get_category_layers(self, category: str):
        return self.repo.get_by_category(category)
