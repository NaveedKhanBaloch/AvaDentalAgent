"""Retell transport security and durable request serialization. No voice engine."""
import hashlib
import hmac
import json
import re
import time
from datetime import datetime, timezone
from sqlalchemy import text
from fastapi import HTTPException
from app.core.config import get_settings
from app.models.models import Clinic, RetellIntegration, IdempotencyRecord, CallLog


def verify_signature(raw: bytes, signature: str | None):
    # Official Retell raw-body + millisecond timestamp HMAC protocol.
    match = re.fullmatch(r"v=(\d+),d=([0-9a-fA-F]{64})", signature or "")
    key = get_settings().retell_api_key
    if not match or not key or (get_settings().app_env == "production" and key.startswith("dev-")):
        raise HTTPException(401, "Invalid Retell signature")
    stamp, digest = match.groups()
    if abs(time.time() * 1000 - int(stamp)) > 300000:
        raise HTTPException(401, "Expired Retell signature")
    expected = hmac.new(key.encode(), raw + stamp.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, digest.lower()):
        raise HTTPException(401, "Invalid Retell signature")


def integration_context(db, payload, integration_id=None):
    call = payload.get("call") or {}
    if not isinstance(call, dict):
        raise HTTPException(422, "call must be an object")
    agent = call.get("agent_id")
    if not isinstance(agent, str) or not agent:
        raise HTTPException(403, "Signed call.agent_id is required; disable args-only payloads")
    query = db.query(RetellIntegration).filter(RetellIntegration.enabled.is_(True))
    if integration_id:
        query = query.filter(RetellIntegration.id == integration_id)
    elif agent:
        query = query.filter(RetellIntegration.agent_id == agent)
    else:
        raise HTTPException(403, "Trusted integration context required")
    matches = query.all()
    if len(matches) != 1:
        raise HTTPException(403, "Integration is disabled or ambiguous")
    integration = matches[0]
    if agent and agent != integration.agent_id:
        raise HTTPException(403, "Agent does not match integration")
    clinic = db.query(Clinic).filter(Clinic.id == integration.clinic_id,
        Clinic.tenant_id == integration.tenant_id, Clinic.status == "active").first()
    if not clinic:
        raise HTTPException(403, "Clinic unavailable")
    return integration, clinic, call


def transaction_lock(db, value):
    if db.get_bind().dialect.name == "postgresql":
        number = int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], "big", signed=True)
        db.execute(text("SELECT pg_advisory_xact_lock(:number)"), {"number": number})


def idempotent_write(db, clinic, call_id, operation, key, args, execute):
    if not isinstance(key, str) or not 1 <= len(key) <= 128:
        raise HTTPException(422, "A stable idempotency_key of 1-128 characters is required")
    scoped_key = hashlib.sha256(f"{clinic.id}:{call_id}:{operation}:{key}".encode()).hexdigest()
    request_hash = hashlib.sha256(json.dumps(args, sort_keys=True, default=str).encode()).hexdigest()
    transaction_lock(db, scoped_key)
    record = db.query(IdempotencyRecord).filter(IdempotencyRecord.idempotency_key == scoped_key).first()
    if record:
        if record.request_hash != request_hash:
            raise HTTPException(409, "Idempotency key reused with different arguments")
        return json.loads(record.response_reference)
    response = execute()
    db.add(IdempotencyRecord(tenant_id=clinic.tenant_id, operation=operation, idempotency_key=scoped_key,
        request_hash=request_hash, response_reference=json.dumps(response, default=str)))
    db.commit()  # Success response becomes visible only after the domain transaction commits.
    return response


def call_record(db, clinic, call_id):
    transaction_lock(db, f"call:{clinic.id}:{call_id}")
    record = db.query(CallLog).filter(CallLog.clinic_id == clinic.id, CallLog.external_call_id == call_id).first()
    if not record:
        record = CallLog(tenant_id=clinic.tenant_id, clinic_id=clinic.id, external_call_id=call_id,
                         status="registered", event_rank=0)
        db.add(record)
        db.flush()
    return record


def enforce_function_rate_limit(clinic_id, call_id):
    from redis import Redis, RedisError
    settings = get_settings()
    if settings.app_env == "test":
        return
    key = "retell:rate:" + hashlib.sha256(f"{clinic_id}:{call_id}:{int(time.time() // 60)}".encode()).hexdigest()
    try:
        redis = Redis.from_url(settings.redis_url, socket_connect_timeout=0.5, socket_timeout=0.5)
        with redis.pipeline(transaction=True) as pipeline:
            pipeline.incr(key)
            pipeline.expire(key, 120)
            count, _ = pipeline.execute()
        redis.close()
    except RedisError:
        raise HTTPException(503, "Function temporarily unavailable; retry with the same idempotency key")
    if count > settings.retell_function_rate_limit:
        raise HTTPException(429, "Function rate limit exceeded")
