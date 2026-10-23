from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import Clinic, InsuranceProfile, Patient, Tenant
from app.schemas.patient import PatientCreate, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


class InsuranceCreate(BaseModel):
    carrier_name: str
    policy_number: str | None = None
    group_number: str | None = None
    member_name: str | None = None
    subscriber_dob: str | None = None
    relationship_to_patient: str | None = None
    status: str = "pending"
    notes: str | None = None


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
def list_patients(
    search: str | None = Query(default=None, description="Search by first name, last name, email, or phone"),
    db: Session = Depends(get_db),
) -> dict[str, list[dict]]:
    _, clinic = get_default_tenant_and_clinic(db)
    query = db.query(Patient).filter(Patient.clinic_id == clinic.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Patient.first_name.ilike(term),
                Patient.last_name.ilike(term),
                Patient.email.ilike(term),
                Patient.phone.ilike(term),
            )
        )
    patients = query.order_by(Patient.created_at.desc()).all()
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
        "tenant_id": patient.tenant_id,
        "clinic_id": patient.clinic_id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email,
        "preferred_contact_method": patient.preferred_contact_method,
        "notes": patient.notes,
    }


@router.patch("/{patient_id}")
def update_patient(patient_id: str, payload: PatientUpdate, db: Session = Depends(get_db)) -> dict:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return {
        "id": patient.id,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "phone": patient.phone,
        "email": patient.email,
        "preferred_contact_method": patient.preferred_contact_method,
        "notes": patient.notes,
    }


@router.delete("/{patient_id}")
def delete_patient(patient_id: str, db: Session = Depends(get_db)) -> dict:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    db.delete(patient)
    db.commit()
    return {"id": patient_id, "deleted": True}


@router.get("/{patient_id}/insurance")
def get_patient_insurance(patient_id: str, db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    insurance = db.query(InsuranceProfile).filter(InsuranceProfile.patient_id == patient.id).order_by(InsuranceProfile.created_at.desc()).all()
    return {
        "items": [
            {
                "id": record.id,
                "patient_id": record.patient_id,
                "carrier_name": record.carrier_name,
                "policy_number": record.policy_number,
                "group_number": record.group_number,
                "member_name": record.member_name,
                "subscriber_dob": record.subscriber_dob,
                "relationship_to_patient": record.relationship_to_patient,
                "status": record.status,
                "notes": record.notes,
            }
            for record in insurance
        ]
    }


@router.post("/{patient_id}/insurance", status_code=status.HTTP_201_CREATED)
def create_patient_insurance(
    patient_id: str,
    payload: InsuranceCreate,
    db: Session = Depends(get_db),
) -> dict:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    tenant, clinic = get_default_tenant_and_clinic(db)
    record = InsuranceProfile(
        tenant_id=tenant.id,
        clinic_id=clinic.id,
        patient_id=patient.id,
        carrier_name=payload.carrier_name,
        policy_number=payload.policy_number,
        group_number=payload.group_number,
        member_name=payload.member_name,
        subscriber_dob=payload.subscriber_dob,
        relationship_to_patient=payload.relationship_to_patient,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {
        "id": record.id,
        "patient_id": record.patient_id,
        "carrier_name": record.carrier_name,
        "policy_number": record.policy_number,
        "group_number": record.group_number,
        "member_name": record.member_name,
        "subscriber_dob": record.subscriber_dob,
        "relationship_to_patient": record.relationship_to_patient,
        "status": record.status,
        "notes": record.notes,
    }
