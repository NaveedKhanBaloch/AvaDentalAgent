"""Read-only benchmark for an explicitly configured synthetic localhost stack."""
import json
import os
import statistics
import time
from urllib.parse import urlparse
import httpx

origin = os.environ.get("BENCHMARK_API_URL", "http://localhost:58001")
if urlparse(origin).hostname not in {"localhost", "127.0.0.1"}:
    raise RuntimeError("This benchmark is restricted to a synthetic localhost stack")
with httpx.Client(base_url=origin, timeout=5) as client:
    login = client.post("/api/v1/auth/login", json={"email": "admin@harbordentaldemo.local",
        "password": os.environ.get("BENCHMARK_PASSWORD", "Phase1Synthetic123!")})
    login.raise_for_status()
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    providers = client.get("/api/v1/providers").json()["items"]
    services = client.get("/api/v1/services").json()["items"]
    payload = {"preferred_date": "2026-11-10", "provider_id": providers[0]["id"], "service_id": services[0]["id"]}
    durations = []
    for i in range(31):
        start = time.perf_counter()
        response = client.post("/api/v1/appointments/availability", json=payload)
        response.raise_for_status()
        if i:
            durations.append((time.perf_counter()-start)*1000)
    print(json.dumps({"operation": "authenticated availability over localhost HTTP", "samples": len(durations),
        "p50_ms": round(statistics.median(durations), 2),
        "p95_ms": round(statistics.quantiles(durations, n=20)[18], 2),
        "max_ms": round(max(durations), 2)}, indent=2))
