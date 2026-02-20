from sqlmodel import Session, select
from models.db_models.db_model import Layer
import geojson


class LayerService:
    def __init__(self, engine):
        self.engine = engine

    def get_all_active_layers(self):
        """
        Business Logic: Fetch all layers that are marked as active
        to display in the frontend sidebar.
        """
        with Session(self.engine) as session:
            statement = select(Layer).where(Layer.is_visible_by_default == True)
            results = session.exec(statement)
            return results.all()

    def get_layer_stats(self, layer_name: str):
        """
        Example Business Layer processing: 
        Instead of just raw data, calculate something useful.
        """
        with Session(self.engine) as session:
            # We use raw SQL here because spatial functions are specific to PostGIS
            query = f"SELECT count(*), ST_Area(ST_Union(geom)) FROM {layer_name}"
            stats = session.execute(query).fetchone()
            return {
                "count": stats[0],
                "total_area_sq_meters": stats[1]
            }
        

# Modify based on this code:
import os
from typing import List
from sqlalchemy.orm import Session
from repositories.layer_repo import LayerRepository
from schemas.layer import LayerRead, CategorySummary


class LayerService:
    def __init__(self, db: Session):
        self.repo = LayerRepository(db)
        # In a real app, this base URL comes from an env variable
        self.tileserv_base_url = os.getenv("TILESERVER_PUBLIC_URL", "http://localhost:7800")

    def list_categories(self) -> List[CategorySummary]:
        return [CategorySummary(**c) for c in self.repo.get_all_categories()]

    def get_category_layers(self, category: str) -> List[LayerRead]:
        layers = self.repo.get_layers_by_category(category)
        
        layer_list = []
        for layer in layers:
            # We construct the URL dynamically. 
            # pg_tileserv serves rasters at: {base}/functions/postgis_raster_tile/items/{table_name}/{z}/{x}/{y}.pbf
            # Note: The exact path depends on your pg_tileserv config/version.
            tile_path = f"{self.tileserv_base_url}/services/public.{layer.name}/tiles/{{z}}/{{x}}/{{y}}.png"
            
            layer_data = LayerRead(
                id=layer.id,
                name=layer.name,
                display_name=layer.display_name,
                category=layer.category,
                geometry_type=layer.geometry_type,
                is_visible_by_default=layer.is_visible_by_default,
                created_at=layer.created_at,
                tile_url=tile_path
            )
            layer_list.append(layer_data)
            
        return layer_list
    