from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.v1.routes.patients import get_default_tenant_and_clinic
from app.db.session import get_db
from app.models.models import ClinicBusinessHours, DentalService, Provider

router = APIRouter(tags=["catalog"])


@router.get("/providers")
def list_providers(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    providers = db.query(Provider).filter(Provider.clinic_id == clinic.id, Provider.active_status.is_(True)).order_by(Provider.name.asc()).all()
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


@router.get("/services")
def list_services(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    services = db.query(DentalService).filter(DentalService.clinic_id == clinic.id, DentalService.active_status.is_(True)).order_by(DentalService.name.asc()).all()
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
