"""Production engineering calculations and alert rules.

Everything here is pure logic over records, so it is easy to unit test and has
no knowledge of HTTP. Rates are averaged over a "recent window" of days so a
single noisy day does not swing the dashboard.
"""

from collections.abc import Sequence
from datetime import date, timedelta
from statistics import fmean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import ProductionRecord, Well, WellStatus
from app.schemas import Alert, ProductionPoint, WellSummary


# ---------- Ratios ----------
def water_cut(oil_bbl: float, water_bbl: float) -> float | None:
    """Fraction of produced liquid that is water. None when no liquid was produced."""
    liquid = oil_bbl + water_bbl
    return round(water_bbl / liquid, 4) if liquid > 0 else None


def gas_oil_ratio(oil_bbl: float, gas_mcf: float) -> float | None:
    """Gas-oil ratio in standard cubic feet per stock-tank barrel (scf/bbl)."""
    return round(gas_mcf * 1000 / oil_bbl, 1) if oil_bbl > 0 else None


def to_point(r: ProductionRecord) -> ProductionPoint:
    return ProductionPoint(
        date=r.date,
        oil_bbl=r.oil_bbl,
        gas_mcf=r.gas_mcf,
        water_bbl=r.water_bbl,
        hours_on=r.hours_on,
        water_cut=water_cut(r.oil_bbl, r.water_bbl),
        gor=gas_oil_ratio(r.oil_bbl, r.gas_mcf),
    )


# ---------- Per-well summary ----------
def recent_records(db: Session, well_id: int, days: int) -> list[ProductionRecord]:
    """The last `days` records for a well, oldest first."""
    rows = db.scalars(
        select(ProductionRecord)
        .where(ProductionRecord.well_id == well_id)
        .order_by(ProductionRecord.date.desc())
        .limit(days)
    ).all()
    return list(reversed(rows))


def summarize_well(db: Session, well: Well, settings: Settings) -> WellSummary:
    recent = recent_records(db, well.id, settings.recent_window_days)
    cum_oil = db.scalar(
        select(func.coalesce(func.sum(ProductionRecord.oil_bbl), 0.0)).where(
            ProductionRecord.well_id == well.id
        )
    )
    summary = WellSummary.model_validate(well, from_attributes=True)
    summary.cum_oil = round(cum_oil or 0.0, 1)
    if not recent:
        return summary
    summary.last_date = recent[-1].date
    if well.status == WellStatus.shut_in:
        return summary  # a shut-in well is not producing, whatever it last reported

    oil = fmean(r.oil_bbl for r in recent)
    gas = fmean(r.gas_mcf for r in recent)
    water = fmean(r.water_bbl for r in recent)
    summary.oil_rate = round(oil, 1)
    summary.gas_rate = round(gas, 1)
    summary.water_rate = round(water, 1)
    summary.water_cut = water_cut(oil, water)
    summary.gor = gas_oil_ratio(oil, gas)
    summary.uptime = round(fmean(r.hours_on for r in recent) / 24, 3)
    return summary


# ---------- Alerts ----------
def pct_change(recent: float, baseline: float) -> float:
    return (recent - baseline) / baseline * 100 if baseline > 0 else 0.0


def evaluate_alerts(
    well: Well, records: Sequence[ProductionRecord], settings: Settings
) -> list[Alert]:
    """Apply the alert rules to one well's records (oldest first).

    Rules:
    - no_production: an active well reported zero oil and gas on its last 3 days.
    - production_drop: recent average oil rate fell versus the preceding baseline window.
    - high_water_cut: recent water cut is above the configured limit.
    """
    if well.status != WellStatus.active or not records:
        return []

    def make(kind, severity, message) -> Alert:
        return Alert(
            well_id=well.id,
            well_name=well.name,
            field=well.field,
            kind=kind,
            severity=severity,
            message=message,
        )

    last3 = records[-3:]
    if len(last3) == 3 and all(r.oil_bbl == 0 and r.gas_mcf == 0 for r in last3):
        return [make("no_production", "critical", "No oil or gas reported for 3 days")]

    alerts: list[Alert] = []
    n_recent = settings.recent_window_days
    recent = records[-n_recent:]
    baseline = records[-(n_recent + settings.baseline_window_days) : -n_recent]

    recent_oil = fmean(r.oil_bbl for r in recent)
    if len(baseline) >= n_recent:  # need enough history to compare against
        base_oil = fmean(r.oil_bbl for r in baseline)
        change = pct_change(recent_oil, base_oil)
        if change <= -settings.drop_critical_pct:
            alerts.append(
                make("production_drop", "critical", f"Oil rate down {abs(change):.0f}% vs baseline")
            )
        elif change <= -settings.drop_warning_pct:
            alerts.append(
                make("production_drop", "warning", f"Oil rate down {abs(change):.0f}% vs baseline")
            )

    wc = water_cut(recent_oil, fmean(r.water_bbl for r in recent))
    if wc is not None and wc > settings.high_water_cut:
        alerts.append(make("high_water_cut", "warning", f"Water cut at {wc:.0%}"))
    return alerts


def all_alerts(db: Session, settings: Settings, field: str | None = None) -> list[Alert]:
    query = select(Well).order_by(Well.name)
    if field:
        query = query.where(Well.field == field)
    window = settings.recent_window_days + settings.baseline_window_days
    alerts: list[Alert] = []
    for well in db.scalars(query):
        alerts.extend(evaluate_alerts(well, recent_records(db, well.id, window), settings))
    # Critical first, then by well name
    return sorted(alerts, key=lambda a: (a.severity != "critical", a.well_name))


# ---------- Field-level time series ----------
def field_series(
    db: Session, field: str | None = None, days: int | None = None
) -> list[ProductionPoint]:
    """Daily totals across all wells (optionally one field), for the last `days` days."""
    query = (
        select(
            ProductionRecord.date,
            func.sum(ProductionRecord.oil_bbl),
            func.sum(ProductionRecord.gas_mcf),
            func.sum(ProductionRecord.water_bbl),
        )
        .join(Well)
        .group_by(ProductionRecord.date)
        .order_by(ProductionRecord.date)
    )
    if field:
        query = query.where(Well.field == field)
    if days:
        latest = db.scalar(select(func.max(ProductionRecord.date)))
        if latest:
            query = query.where(ProductionRecord.date > latest - timedelta(days=days))

    return [
        ProductionPoint(
            date=d,
            oil_bbl=round(oil, 1),
            gas_mcf=round(gas, 1),
            water_bbl=round(water, 1),
            water_cut=water_cut(oil, water),
            gor=gas_oil_ratio(oil, gas),
        )
        for d, oil, gas, water in db.execute(query)
    ]


def latest_date(db: Session) -> date | None:
    return db.scalar(select(func.max(ProductionRecord.date)))
