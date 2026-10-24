from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=120)
    last_name: str = Field(..., min_length=1, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    preferred_contact_method: str = "phone"
    notes: str | None = None
    date_of_birth: date | None = None
    do_not_contact: bool = False
    email_consent: bool = False
    sms_consent: bool = False

    @field_validator("date_of_birth")
    @classmethod
    def valid_birth_date(cls, value):
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @field_validator("phone", "email", "notes", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return None if stripped == "" else stripped
        return value


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=120)
    last_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    preferred_contact_method: str | None = None
    notes: str | None = None
    date_of_birth: date | None = None
    do_not_contact: bool | None = None
    email_consent: bool | None = None
    sms_consent: bool | None = None
    expected_revision: int | None = Field(default=None, ge=1)

    @field_validator("date_of_birth")
    @classmethod
    def valid_birth_date(cls, value):
        if value and value > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return value

    @field_validator("phone", "email", "notes", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value):
        if isinstance(value, str):
            stripped = value.strip()
            return None if stripped == "" else stripped
        return value


class PatientOut(PatientCreate):
    id: str
    tenant_id: str
    clinic_id: str
    created_at: datetime
