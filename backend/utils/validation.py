from typing import Optional
from sqlmodel import Session, select
from models.db_models.db_model import Layer


def get_layer_by_name(session: Session, name: str) -> Optional[Layer]:
    """Return Layer model if exists, else None. Centralized whitelist check."""
    stmt = select(Layer).where(Layer.name == name)
    return session.exec(stmt).first()


def list_layer_names(session: Session) -> list[str]:
    stmt = select(Layer.name)
    rows = session.exec(stmt).all()
    return [r for r in rows]
