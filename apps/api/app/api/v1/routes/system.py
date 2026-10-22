from fastapi import APIRouter

router = APIRouter(tags=["system"])


@router.get("/system/info")
def system_info() -> dict:
    return {
        "app": "DentalVoice AI",
        "environment": "development",
        "version": "0.1.0",
        "tenant_mode": "multi-tenant",
    }
