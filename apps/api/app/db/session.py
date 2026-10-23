from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.core.config import get_settings

settings = get_settings()
# Never silently switch databases when PostgreSQL is unavailable.
options = {"connect_args": {"check_same_thread": False}} if settings.database_url.startswith("sqlite") else {"pool_size": 10, "max_overflow": 10, "connect_args": {"connect_timeout": 5}}
engine = create_engine(settings.database_url, pool_pre_ping=True, **options)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        try:
            yield db
        except Exception:
            db.rollback()
            raise
