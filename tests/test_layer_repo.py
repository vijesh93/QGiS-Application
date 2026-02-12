import pytest
from sqlmodel import SQLModel, create_engine, Session
from backend.models.db_models.db_model import Layer


@pytest.fixture
def in_memory_engine():
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return engine


def test_layer_repository_basic(in_memory_engine):
    with Session(in_memory_engine) as session:
        # insert a layer metadata row
        layer = Layer(name="test_layer", display_name="Test Layer", category="Test", geometry_type="Point", is_visible_by_default=True)
        session.add(layer)
        session.commit()

        # simple query using SQLModel session works
        rows = session.exec("SELECT * FROM layer_metadata").all()
        assert len(rows) == 1
        assert rows[0].display_name == "Test Layer"
