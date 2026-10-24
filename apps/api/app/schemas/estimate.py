from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator


class EstimateLine(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    service_id: str
    quantity: Decimal = Field(default=Decimal(1), gt=0, le=10000, max_digits=12, decimal_places=3)
    unit_price: Decimal | None = Field(
        default=None, ge=0, le=Decimal(999999999), max_digits=18, decimal_places=4
    )
    discount_percent: Decimal = Field(
        default=Decimal(0), ge=0, le=100, max_digits=7, decimal_places=4
    )
    tax_label: str = Field(default="none", max_length=100)


class EstimateDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    patient_id: str
    items: list[EstimateLine] = Field(min_length=1, max_length=100)
    issue_date: date
    valid_until: date | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    revision_reason: str | None = Field(default=None, max_length=2000)


class EstimateAction(BaseModel):
    expected_revision: int = Field(ge=1)
    version: int = Field(ge=1)
    status: Literal["sent", "accepted", "declined", "expired", "cancelled"]
    confirmed: StrictBool
    acknowledged_by_name: str | None = Field(default=None, max_length=255)
    method: str | None = Field(default=None, max_length=100)
    reason: str | None = Field(default=None, max_length=2000)


class PolicyInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")
    currency: str = Field(min_length=3, max_length=10)
    minor_units: int = Field(ge=0, le=4)
    tax_rates: dict[str, Decimal]
    max_discount_percent: Decimal = Field(ge=0, le=100, max_digits=7, decimal_places=4)
    terms: str = Field(max_length=10000)
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    clinically_approved: StrictBool
    expected_revision: int | None = None

    @field_validator("tax_rates")
    @classmethod
    def validate_rates(cls, v):
        if (
            len(v) > 30
            or not v
            or any(
                not k
                or len(k) > 100
                or not r.is_finite()
                or r < 0
                or r > 100
                or r.as_tuple().exponent < -4
                for k, r in v.items()
            )
        ):
            raise ValueError("Approved finite tax rates between 0 and 100 are required")
        return v
