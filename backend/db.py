from sqlmodel import Session, create_engine
import os
from urllib.parse import quote_plus


# Central DB engine and session provider used across the backend
user_name = os.getenv("DB_USER")
encoded_password = os.getenv("DB_PASSWORD_URL")

# Try to get the full URL from env, otherwise build it using f-string
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    DATABASE_URL = f"postgresql://{user_name}:{encoded_password}@db:5432/geoportal"

else:
    # TODO: Figure out what is better way to enter a password for DB.
    raise NotImplementedError

# print(f"Connecting to: {DATABASE_URL.replace(encoded_password, '****')}") # Safety print
engine = create_engine(DATABASE_URL)


def get_session():
    with Session(engine) as session:
        yield session
