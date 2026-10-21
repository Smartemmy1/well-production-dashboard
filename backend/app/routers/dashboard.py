"""Field-level overview and alerts."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.models import Well, WellStatus
from app.schemas import Alert, DashboardSummary
from app.services import analytics

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardSummary)
def dashboard(
    field: str | None = None,
    days: int = Query(default=90, ge=7, le=3650),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Headline rates plus a daily field-total series for charting."""
    well_filter = [Well.field == field] if field else []
    total = db.scalar(select(func.count(Well.id)).where(*well_filter)) or 0
    active = (
        db.scalar(select(func.count(Well.id)).where(Well.status == WellStatus.active, *well_filter))
        or 0
    )

    series = analytics.field_series(db, field=field, days=days)
    # Headline rates are the average of the most recent window, like the well table.
    recent = series[-settings.recent_window_days :]
    n = len(recent) or 1
    oil = sum(p.oil_bbl for p in recent) / n
    gas = sum(p.gas_mcf for p in recent) / n
    water = sum(p.water_bbl for p in recent) / n

    return DashboardSummary(
        as_of=series[-1].date if series else None,
        active_wells=active,
        total_wells=total,
        oil_rate=round(oil, 1),
        gas_rate=round(gas, 1),
        water_rate=round(water, 1),
        water_cut=analytics.water_cut(oil, water),
        alert_count=len(analytics.all_alerts(db, settings, field)),
        series=series,
    )


@router.get("/alerts", response_model=list[Alert])
def alerts(
    field: str | None = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Wells that need an engineer's attention, critical first."""
    return analytics.all_alerts(db, settings, field)
