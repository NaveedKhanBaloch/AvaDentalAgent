from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.catalog import router as catalog_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.patients import router as patients_router
from app.api.v1.routes.retell import router as retell_router
from app.api.v1.routes.scheduler import router as scheduler_router
from app.api.v1.routes.system import router as system_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.init_db import seed_demo_data
from app.db.session import engine

settings = get_settings()

app = FastAPI(
    title="DentalVoice AI API",
    version="0.1.0",
    description="Multi-tenant dental clinic receptionist SaaS API",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        seed_demo_data()
    except Exception:  # pragma: no cover - defensive startup guard
        pass


app.include_router(health_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(patients_router, prefix="/api/v1")
app.include_router(scheduler_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(retell_router, prefix="/api/v1")


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "DentalVoice AI backend is running."}
