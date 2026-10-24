from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    patient_id: str | None = None
    contact_name: str | None = Field(None, max_length=255)
    contact_phone: str | None = Field(None, max_length=30)
    reason: str = Field(min_length=1, max_length=2000)
    priority: Literal["low", "normal", "high"] = "normal"
    followup_type: str = Field(default="general_callback", min_length=1, max_length=80)
    due_at: datetime | None = None
    assigned_user_id: str | None = None
    appointment_id: str | None = None
    call_id: str | None = None
    estimate_id: str | None = None
    notes: str | None = Field(None, max_length=4000)

    @field_validator("due_at")
    @classmethod
    def aware(cls, v):
        if v and not v.tzinfo:
            raise ValueError("Due time requires a timezone offset")
        return v


class FollowUpUpdate(FollowUpCreate):
    expected_revision: int = Field(ge=1)
    status: Literal["pending", "in_progress", "completed", "cancelled"] = "pending"


class RecallCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    patient_id: str
    recall_type: str = Field(min_length=1, max_length=80)
    reason: str | None = Field(None, max_length=2000)
    due_date: date | None = None
    recall_rule_id: str | None = None
    assigned_user_id: str | None = None
    origin_appointment_id: str | None = None
    appointment_id: str | None = None
    contact_preference: Literal["phone", "email", "sms"] = "phone"


class RecallUpdate(RecallCreate):
    expected_revision: int = Field(ge=1)
    status: Literal[
        "due", "contact_pending", "contacted", "scheduled", "completed", "cancelled"
    ] = "due"
    completion_reason: str | None = Field(None, max_length=2000)
    log_contact_attempt: bool = False
