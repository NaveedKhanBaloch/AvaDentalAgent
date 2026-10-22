from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    preferred_contact_method: str = "phone"
    notes: str | None = None


class PatientUpdate(PatientCreate):
    pass


class PatientOut(PatientCreate):
    id: str
    tenant_id: str
    clinic_id: str
    created_at: datetime
