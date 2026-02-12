from sqlmodel import Session, create_engine
import os

# Central DB engine and session provider used across the backend
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:password@db:5432/geoportal")
engine = create_engine(DATABASE_URL)

def get_session():
    with Session(engine) as session:
        yield session
