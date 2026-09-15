from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

def get_engine_args(database_url: str) -> dict:
    """
    Returns engine configuration arguments tailored for the target database dialect.
    Configures production connection pooling for PostgreSQL while preserving SQLite behavior.
    """
    url_lower = (database_url or "").lower()
    if "sqlite" in url_lower:
        return {"connect_args": {"check_same_thread": False}}
    elif "postgresql" in url_lower or "postgres" in url_lower:
        return {
            "pool_pre_ping": True,
            "pool_size": 20,
            "max_overflow": 10,
        }
    return {}

engine = create_engine(
    settings.DATABASE_URL,
    **get_engine_args(settings.DATABASE_URL)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

