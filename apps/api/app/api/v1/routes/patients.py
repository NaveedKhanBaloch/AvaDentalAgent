from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Clinic, Patient, Tenant
from app.schemas.patient import PatientCreate

router = APIRouter(prefix="/patients", tags=["patients"])


def get_default_tenant_and_clinic(db: Session) -> tuple[Tenant, Clinic]:
    tenant = db.query(Tenant).filter(Tenant.slug == "harbor-dental-demo").first()
    if tenant is None:
        tenant = Tenant(name="Harbor Dental Group", slug="harbor-dental-demo")
        db.add(tenant)
        db.flush()

    clinic = db.query(Clinic).filter(Clinic.tenant_id == tenant.id, Clinic.name == "Harbor Dental Demo").first()
    if clinic is None:
        clinic = Clinic(
            tenant_id=tenant.id,
            name="Harbor Dental Demo",
            address="125 Shoreline Ave",
            city="Boston",
            state="MA",
            country="US",
            timezone="America/New_York",
            phone="(617) 555-0100",
            email="frontdesk@harbordentaldemo.local",
            currency="USD",
        )
        db.add(clinic)
        db.flush()

    return tenant, clinic


@router.get("")
def list_patients(db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    patients = db.query(Patient).filter(Patient.clinic_id == clinic.id).order_by(Patient.created_at.desc()).all()
    return {"items": [{
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email,
        "preferred_contact_method": patient.preferred_contact_method,
        "notes": patient.notes,
    } for patient in patients]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> dict:
    tenant, clinic = get_default_tenant_and_clinic(db)
    patient = Patient(
        tenant_id=tenant.id,
        clinic_id=clinic.id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        preferred_contact_method=payload.preferred_contact_method,
        notes=payload.notes,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return {
        "id": patient.id,
        "tenant_id": patient.tenant_id,
        "clinic_id": patient.clinic_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email,
        "preferred_contact_method": patient.preferred_contact_method,
        "notes": patient.notes,
    }


@router.get("/{patient_id}")
def get_patient(patient_id: str, db: Session = Depends(get_db)) -> dict:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email,
    }
