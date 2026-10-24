from fastapi import FastAPI, Depends
from app.core.authorization import bind_request_user
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.catalog import router as catalog_router
from app.api.v1.routes.dashboard import router as dashboard_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.estimates import router as estimates_router
from app.api.v1.routes.operations import router as operations_router
from app.api.v1.routes.patients import router as patients_router
from app.api.v1.routes.patient_operations import router as patient_operations_router
from app.api.v1.routes.retell import router as retell_router
from app.api.v1.routes.scheduler import router as scheduler_router
from app.api.v1.routes.staff import router as staff_router
from app.api.v1.routes.system import router as system_router
from app.core.config import get_settings

settings = get_settings()
if settings.app_env == "production":
    if len(settings.jwt_secret_key) < 32 or settings.jwt_secret_key.startswith("change-me"):
        raise RuntimeError("Production requires a strong JWT_SECRET_KEY")
    if not settings.database_url.startswith("postgresql"):
        raise RuntimeError("Production requires PostgreSQL")

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


app.include_router(health_router, prefix="/api/v1")
app.include_router(system_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(estimates_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(patient_operations_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(operations_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(patients_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(scheduler_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(staff_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(dashboard_router, prefix="/api/v1", dependencies=[Depends(bind_request_user)])
app.include_router(retell_router, prefix="/api/v1")


@app.get("/")
def index() -> dict[str, str]:
    return {"message": "DentalVoice AI backend is running."}
