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
        