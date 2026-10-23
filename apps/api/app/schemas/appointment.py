from datetime import datetime

from pydantic import BaseModel, Field


class AppointmentCreate(BaseModel):
    patient_id: str
    provider_id: str | None = None
    service_id: str | None = None
    start_time: datetime
    end_time: datetime
    status: str = "scheduled"
    source: str = "dashboard"
    notes: str | None = None


class AppointmentUpdate(BaseModel):
    provider_id: str | None = None
    service_id: str | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    status: str | None = None
    notes: str | None = None


class AppointmentStatusUpdate(BaseModel):
    status: str
    notes: str | None = None


class AvailabilityRequest(BaseModel):
    clinic_id: str | None = None
    provider_id: str | None = None
    service_id: str | None = None
    preferred_date: str = Field(..., description="Date in YYYY-MM-DD format")
    time_preference: str | None = None


class Slot(BaseModel):
    slot_id: str
    start_time: datetime
    end_time: datetime
    provider_id: str | None = None


class AvailabilityResponse(BaseModel):
    success: bool = True
    status: str = "available"
    slots: list[Slot] = []
    message: str = "Available appointments found."
