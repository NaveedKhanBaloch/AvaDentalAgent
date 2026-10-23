from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.api.v1.routes.staff import require_permission
from app.db.session import get_db
from app.models.models import ClinicBusinessHours, DentalService, Provider, ScheduleException

router = APIRouter(tags=["catalog"])


class CalendarBlockCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    reason: str | None = None
    exception_type: str = "time_off"


class ProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    title: str | None = None
    specialty: str | None = None
    active_status: bool = True


class ProviderUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    title: str | None = None
    specialty: str | None = None
    active_status: bool | None = None


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    default_duration_minutes: int = 30
    indicative_price: float = 0.0
    currency: str = "USD"
    active_status: bool = True


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    default_duration_minutes: int | None = None
    indicative_price: float | None = None
    currency: str | None = None
    active_status: bool | None = None


@router.get("/providers")
def list_providers(
    search: str | None = Query(default=None, description="Search by provider name or specialty"),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    query = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(Provider.name.ilike(term), Provider.specialty.ilike(term), Provider.title.ilike(term)))
    providers = query.order_by(Provider.name.asc()).all()
    return {
        "items": [
            {
                "id": provider.id,
                "name": provider.name,
                "title": provider.title,
                "specialty": provider.specialty,
                "active_status": provider.active_status,
            }
            for provider in providers
        ]
    }


@router.post("/providers", status_code=status.HTTP_201_CREATED)
def create_provider(payload: ProviderCreate, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    provider = Provider(
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        name=payload.name,
        title=payload.title,
        specialty=payload.specialty,
        active_status=payload.active_status,
    )
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return {"id": provider.id, "name": provider.name, "title": provider.title, "specialty": provider.specialty}


@router.patch("/providers/{provider_id}")
def update_provider(provider_id: str, payload: ProviderUpdate, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(provider, field, value)
    db.commit(); db.refresh(provider)
    return {"id": provider.id, "name": provider.name, "title": provider.title, "specialty": provider.specialty, "active_status": provider.active_status}


@router.delete("/providers/{provider_id}")
def delete_provider(provider_id: str, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    db.delete(provider)
    db.commit()
    return {"id": provider_id, "deleted": True}


@router.get("/services")
def list_services(
    search: str | None = Query(default=None, description="Search by service name or description"),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    query = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True))
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(DentalService.name.ilike(term), DentalService.description.ilike(term)))
    services = query.order_by(DentalService.name.asc()).all()
    return {
        "items": [
            {
                "id": service.id,
                "name": service.name,
                "description": service.description,
                "default_duration_minutes": service.default_duration_minutes,
                "indicative_price": service.indicative_price,
                "currency": service.currency,
                "active_status": service.active_status,
            }
            for service in services
        ]
    }


@router.post("/services", status_code=status.HTTP_201_CREATED)
def create_service(payload: ServiceCreate, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    service = DentalService(
        tenant_id=clinic.tenant_id,
        clinic_id=clinic.id,
        name=payload.name,
        description=payload.description,
        default_duration_minutes=payload.default_duration_minutes,
        indicative_price=payload.indicative_price,
        currency=payload.currency,
        active_status=payload.active_status,
    )
    db.add(service)
    db.commit(); db.refresh(service)
    return {"id": service.id, "name": service.name, "description": service.description, "default_duration_minutes": service.default_duration_minutes}


@router.patch("/services/{service_id}")
def update_service(service_id: str, payload: ServiceUpdate, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(service, field, value)
    db.commit(); db.refresh(service)
    return {"id": service.id, "name": service.name, "description": service.description, "default_duration_minutes": service.default_duration_minutes, "indicative_price": service.indicative_price, "active_status": service.active_status}


@router.delete("/services/{service_id}")
def delete_service(service_id: str, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    service = db.query(DentalService).filter(DentalService.id == service_id, DentalService.clinic_id == clinic.id).first()
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    db.delete(service)
    db.commit()
    return {"id": service_id, "deleted": True}


@router.get("/business-hours")
def list_business_hours(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    hours = db.query(ClinicBusinessHours).filter(ClinicBusinessHours.clinic_id == clinic.id).order_by(ClinicBusinessHours.weekday.asc()).all()
    return {
        "items": [
            {
                "id": item.id,
                "weekday": item.weekday,
                "opening_time": item.opening_time,
                "closing_time": item.closing_time,
                "is_closed": item.is_closed,
            }
            for item in hours
        ]
    }


@router.post("/providers/{provider_id}/calendar/blocks")
def create_provider_calendar_block(
    provider_id: str,
    payload: CalendarBlockCreate,
    db: Session = Depends(get_db),
    current_user: object | None = Depends(require_permission("manage_schedule")),
) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Block end time must be after start time.")

    block = ScheduleException(
        clinic_id=clinic.id,
        provider_id=provider.id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason or "Provider unavailable",
        exception_type=payload.exception_type,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return {
        "id": block.id,
        "provider_id": provider.id,
        "start_time": block.start_time.isoformat(),
        "end_time": block.end_time.isoformat(),
        "reason": block.reason,
        "exception_type": block.exception_type,
    }


@router.get("/providers/{provider_id}/calendar")
def get_provider_calendar(provider_id: str, date: str | None = None, db: Session = Depends(get_db)) -> dict:
    _, clinic = get_default_tenant_and_clinic(db)
    provider = db.query(Provider).filter(Provider.id == provider_id, Provider.clinic_id == clinic.id).first()
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    query = db.query(ScheduleException).filter(ScheduleException.clinic_id == clinic.id, ScheduleException.provider_id == provider.id)
    if date:
        target_day = datetime.fromisoformat(date)
        day_start = target_day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        query = query.filter(ScheduleException.start_time < day_end, ScheduleException.end_time > day_start)

    blocks = query.order_by(ScheduleException.start_time.asc()).all()
    return {
        "provider_id": provider.id,
        "date": date,
        "blocks": [
            {
                "id": block.id,
                "provider_id": block.provider_id,
                "start_time": block.start_time.isoformat(),
                "end_time": block.end_time.isoformat(),
                "reason": block.reason,
                "exception_type": block.exception_type,
            }
            for block in blocks
        ],
    }
