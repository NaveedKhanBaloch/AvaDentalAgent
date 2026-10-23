from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from redis import Redis, RedisError
from app.db.session import get_db
from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])

@router.get("/live")
def health_live():
    return {"status": "alive"}

@router.get("/ready")
def health_ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        if get_settings().app_env != "test":
            with Redis.from_url(get_settings().redis_url, socket_connect_timeout=1, socket_timeout=1) as redis:
                redis.ping()
    except Exception:
        raise HTTPException(503, "Dependencies unavailable")
    return {"status": "ready"}
