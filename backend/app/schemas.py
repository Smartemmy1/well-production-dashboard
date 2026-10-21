"""Pydantic schemas: request validation and response shapes."""

from datetime import date as Date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import LiftType, WellStatus


# ---------- Wells ----------
class WellBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, examples=["AR-01"])
    field: str = Field(min_length=1, max_length=100, examples=["Avalon Ridge"])
    lift_type: LiftType = LiftType.natural_flow
    status: WellStatus = WellStatus.active
    start_date: Date


class WellCreate(WellBase):
    pass


class WellUpdate(BaseModel):
    field: str | None = Field(default=None, min_length=1, max_length=100)
    lift_type: LiftType | None = None
    status: WellStatus | None = None


class WellOut(WellBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class WellSummary(WellOut):
    """A well plus its most recent performance figures."""

    last_date: Date | None = None
    oil_rate: float = 0.0  # bbl/d, average over the recent window
    gas_rate: float = 0.0  # Mcf/d
    water_rate: float = 0.0  # bbl/d
    water_cut: float | None = None  # fraction 0-1
    gor: float | None = None  # scf/bbl
    uptime: float | None = None  # fraction 0-1
    cum_oil: float = 0.0  # bbl since first record


# ---------- Production ----------
class ProductionIn(BaseModel):
    date: Date
    oil_bbl: float = Field(ge=0)
    gas_mcf: float = Field(ge=0)
    water_bbl: float = Field(ge=0)
    hours_on: float = Field(default=24, ge=0, le=24)

    @field_validator("date")
    @classmethod
    def not_in_future(cls, value: Date) -> Date:
        if value > Date.today():
            raise ValueError("production date cannot be in the future")
        return value


class ProductionOut(ProductionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    well_id: int


class ProductionPoint(BaseModel):
    """A daily point with derived ratios, used for charts."""

    date: Date
    oil_bbl: float
    gas_mcf: float
    water_bbl: float
    hours_on: float | None = None
    water_cut: float | None = None
    gor: float | None = None


class UploadResult(BaseModel):
    inserted: int
    skipped_duplicates: int
    errors: list[str]


# ---------- Dashboard & alerts ----------
class Alert(BaseModel):
    well_id: int
    well_name: str
    field: str
    kind: Literal["production_drop", "high_water_cut", "no_production"]
    severity: Literal["warning", "critical"]
    message: str


class DashboardSummary(BaseModel):
    as_of: Date | None
    active_wells: int
    total_wells: int
    oil_rate: float
    gas_rate: float
    water_rate: float
    water_cut: float | None
    alert_count: int
    series: list[ProductionPoint]
