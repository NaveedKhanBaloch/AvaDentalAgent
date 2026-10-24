"""Idle maintenance worker with observable Redis heartbeat; no queued bookings."""
import logging
import signal
from threading import Event
from redis import Redis, RedisError
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
stop = Event()
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, lambda *_: stop.set())

settings = get_settings()
redis = Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
logger.info("Maintenance worker started; no slow webhook jobs are currently configured")
while not stop.is_set():
    try:
        redis.set("dentalvoice:worker:heartbeat", "alive", ex=90)
        if settings.sandbox_reminders_enabled:
            from app.db.session import SessionLocal
            from app.models.models import Clinic
            from app.services.reminders import prepare_reminders
            with SessionLocal() as db:
                for clinic in db.query(Clinic).filter_by(status="active").order_by(Clinic.id).all():
                    try:
                        prepare_reminders(db, clinic)
                    except Exception:
                        db.rollback()
                        logger.warning("Sandbox preparation failed; retrying next cycle")
    except RedisError:
        logger.warning("Worker Redis connection unavailable; retrying")
    stop.wait(30)
redis.close()
