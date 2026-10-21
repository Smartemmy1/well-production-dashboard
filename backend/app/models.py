"""ORM models: a Well has many daily ProductionRecords."""

import enum
from datetime import date

from sqlalchemy import Date, Enum, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class WellStatus(enum.StrEnum):
    active = "active"
    shut_in = "shut_in"


class LiftType(enum.StrEnum):
    natural_flow = "natural_flow"
    esp = "esp"  # electric submersible pump
    gas_lift = "gas_lift"
    rod_pump = "rod_pump"


class Well(Base):
    __tablename__ = "wells"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    field: Mapped[str] = mapped_column(String(100), index=True)
    lift_type: Mapped[LiftType] = mapped_column(Enum(LiftType), default=LiftType.natural_flow)
    status: Mapped[WellStatus] = mapped_column(Enum(WellStatus), default=WellStatus.active)
    start_date: Mapped[date] = mapped_column(Date)

    records: Mapped[list["ProductionRecord"]] = relationship(
        back_populates="well", cascade="all, delete-orphan", order_by="ProductionRecord.date"
    )


class ProductionRecord(Base):
    """One day of measured production for one well."""

    __tablename__ = "production_records"
    __table_args__ = (UniqueConstraint("well_id", "date", name="uq_well_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    well_id: Mapped[int] = mapped_column(ForeignKey("wells.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    oil_bbl: Mapped[float] = mapped_column(Float, default=0.0)
    gas_mcf: Mapped[float] = mapped_column(Float, default=0.0)
    water_bbl: Mapped[float] = mapped_column(Float, default=0.0)
    hours_on: Mapped[float] = mapped_column(Float, default=24.0)

    well: Mapped[Well] = relationship(back_populates="records")
