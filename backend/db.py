import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine


# 1. Get components (optional, but good for debugging)
user_name = os.getenv("DB_USER")
encoded_password = os.getenv("DB_PASSWORD_URL")

# 2. Get the URL. If it doesn't exist, build it.
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DATABASE_URL = f"postgresql://{user_name}:{encoded_password}@db:5432/geoportal"

print(f"✅ Backend connecting to: {DATABASE_URL.split('@')[1]}") # Prints 'db:5432/geoportal' for safety

# 3. Create engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    with Session(engine) as session:
        yield session


def sqlalchemy():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
