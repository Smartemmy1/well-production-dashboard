"""Endpoints for wells and their daily production."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import ProductionRecord, Well, WellStatus
from app.schemas import (
    ProductionIn,
    ProductionOut,
    ProductionPoint,
    WellCreate,
    WellOut,
    WellSummary,
    WellUpdate,
)
from app.services.analytics import summarize_well, to_point

router = APIRouter(prefix="/api/wells", tags=["wells"])


def get_well_or_404(db: Session, well_id: int) -> Well:
    well = db.get(Well, well_id)
    if well is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Well {well_id} not found")
    return well


@router.get("", response_model=list[WellSummary])
def list_wells(
    field: str | None = None,
    well_status: WellStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """All wells with their recent rates, water cut, GOR and cumulative oil."""
    query = select(Well).order_by(Well.name)
    if field:
        query = query.where(Well.field == field)
    if well_status:
        query = query.where(Well.status == well_status)
    return [summarize_well(db, w, settings) for w in db.scalars(query)]


@router.get("/fields", response_model=list[str])
def list_fields(db: Session = Depends(get_db)):
    return list(db.scalars(select(Well.field).distinct().order_by(Well.field)))


@router.post("", response_model=WellOut, status_code=status.HTTP_201_CREATED)
def create_well(payload: WellCreate, db: Session = Depends(get_db)):
    well = Well(**payload.model_dump())
    db.add(well)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Well '{payload.name}' already exists"
        ) from None
    db.refresh(well)
    return well


@router.get("/{well_id}", response_model=WellSummary)
def get_well(
    well_id: int, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)
):
    return summarize_well(db, get_well_or_404(db, well_id), settings)


@router.patch("/{well_id}", response_model=WellOut)
def update_well(well_id: int, payload: WellUpdate, db: Session = Depends(get_db)):
    well = get_well_or_404(db, well_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(well, key, value)
    db.commit()
    db.refresh(well)
    return well


@router.delete("/{well_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_well(well_id: int, db: Session = Depends(get_db)):
    db.delete(get_well_or_404(db, well_id))
    db.commit()


@router.get("/{well_id}/production", response_model=list[ProductionPoint])
def get_production(
    well_id: int,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    """Daily production for one well, with water cut and GOR per day."""
    get_well_or_404(db, well_id)
    if start and end and start > end:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "start must be before end")
    query = (
        select(ProductionRecord)
        .where(ProductionRecord.well_id == well_id)
        .order_by(ProductionRecord.date)
    )
    if start:
        query = query.where(ProductionRecord.date >= start)
    if end:
        query = query.where(ProductionRecord.date <= end)
    return [to_point(r) for r in db.scalars(query)]


@router.post(
    "/{well_id}/production", response_model=ProductionOut, status_code=status.HTTP_201_CREATED
)
def add_production(well_id: int, payload: ProductionIn, db: Session = Depends(get_db)):
    """Record one day of production. A second entry for the same date is rejected."""
    get_well_or_404(db, well_id)
    record = ProductionRecord(well_id=well_id, **payload.model_dump())
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Production for {payload.date} already recorded"
        ) from None
    db.refresh(record)
    return record
