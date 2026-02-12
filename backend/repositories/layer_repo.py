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
    