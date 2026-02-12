from fastapi.testclient import TestClient
from backend.main import app
from sqlmodel import SQLModel, create_engine, Session
from backend.db import engine as real_engine
from backend.models.db_models.db_model import Layer


def override_get_session():
    """Override dependency to use an in-memory SQLite DB for tests."""
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        # seed a layer
        layer = Layer(name="test_layer", display_name="Test Layer", category="Test", geometry_type="Point", is_visible_by_default=True)
        session.add(layer)
        session.commit()
        yield session


def test_list_layers_endpoint(monkeypatch):
    # override the dependency
    app.dependency_overrides = {}
    from backend.db import get_session

    app.dependency_overrides[get_session] = override_get_session

    client = TestClient(app)
    resp = client.get("/api/v1/layers")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["name"] == "test_layer"
