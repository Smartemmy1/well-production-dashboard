"""Generate a realistic demo dataset: 12 wells, one year of daily production.

Rates follow Arps hyperbolic decline, q(t) = qi / (1 + b * Di * t) ** (1 / b),
with rising water cut, measurement noise and occasional downtime. A few wells
are given deliberate problems so the alert rules have something to find.

Field and well names are fictional. Run directly to reset the database:

    python -m app.seed
"""

import random
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LiftType, ProductionRecord, Well, WellStatus

HISTORY_DAYS = 365


@dataclass
class WellPlan:
    name: str
    field: str
    lift: LiftType
    qi: float  # initial oil rate, bbl/d
    di: float  # nominal annual decline
    b: float  # Arps b-factor
    wc0: float  # starting water cut
    wc_growth: float  # water cut added per year
    gor: float  # scf/bbl
    online_days_ago: int = HISTORY_DAYS
    scenario: str | None = None  # "drop", "slight_drop", "watered_out", "dead", "shut_in"


PLANS = [
    WellPlan("AR-01", "Avalon Ridge", LiftType.natural_flow, 2800, 0.45, 0.6, 0.05, 0.10, 850),
    WellPlan(
        "AR-02",
        "Avalon Ridge",
        LiftType.gas_lift,
        1900,
        0.55,
        0.5,
        0.15,
        0.12,
        920,
        scenario="slight_drop",
    ),
    WellPlan("AR-03", "Avalon Ridge", LiftType.esp, 1500, 0.35, 0.8, 0.30, 0.15, 700),
    WellPlan(
        "AR-04",
        "Avalon Ridge",
        LiftType.rod_pump,
        600,
        0.60,
        0.4,
        0.45,
        0.20,
        500,
        scenario="shut_in",
    ),
    WellPlan("GB-01", "Grand Bank East", LiftType.natural_flow, 3200, 0.50, 0.7, 0.02, 0.08, 1300),
    WellPlan("GB-02", "Grand Bank East", LiftType.gas_lift, 2100, 0.40, 0.6, 0.10, 0.10, 1150),
    WellPlan(
        "GB-03", "Grand Bank East", LiftType.esp, 1700, 0.45, 0.5, 0.20, 0.12, 1000, scenario="drop"
    ),
    WellPlan(
        "GB-04",
        "Grand Bank East",
        LiftType.natural_flow,
        2600,
        0.70,
        0.9,
        0.01,
        0.05,
        1400,
        online_days_ago=120,
    ),
    WellPlan("PS-01", "Placentia Shelf", LiftType.esp, 1300, 0.30, 0.5, 0.35, 0.15, 650),
    WellPlan(
        "PS-02",
        "Placentia Shelf",
        LiftType.esp,
        900,
        0.25,
        0.4,
        0.70,
        0.18,
        600,
        scenario="watered_out",
    ),
    WellPlan("PS-03", "Placentia Shelf", LiftType.gas_lift, 1600, 0.40, 0.6, 0.18, 0.12, 780),
    WellPlan(
        "PS-04",
        "Placentia Shelf",
        LiftType.rod_pump,
        450,
        0.35,
        0.5,
        0.40,
        0.10,
        550,
        scenario="dead",
    ),
]


def arps_rate(qi: float, di_annual: float, b: float, t_days: float) -> float:
    di_daily = di_annual / 365
    return qi / (1 + b * di_daily * t_days) ** (1 / b)


def generate_records(plan: WellPlan, end: date, rng: random.Random) -> list[ProductionRecord]:
    records = []
    start = end - timedelta(days=plan.online_days_ago - 1)
    for i in range(plan.online_days_ago):
        day = start + timedelta(days=i)
        days_left = plan.online_days_ago - 1 - i  # 0 on the last day

        if plan.scenario == "shut_in" and days_left < 60:
            break  # shut in two months ago: no more reports

        oil = arps_rate(plan.qi, plan.di, plan.b, i) * rng.gauss(1.0, 0.03)
        wc = min(0.95, plan.wc0 + plan.wc_growth * i / 365 + rng.gauss(0, 0.01))
        gor = plan.gor * (1 + 0.15 * i / 365) * rng.gauss(1.0, 0.04)

        if plan.scenario == "drop" and days_left < 7:
            oil *= 0.38  # pump failure: rate falls by more than half
        if plan.scenario == "slight_drop" and days_left < 7:
            oil *= 0.68
        if plan.scenario == "watered_out" and days_left < 45:
            wc = min(0.93, 0.86 + rng.gauss(0, 0.01))

        hours = 24.0
        if rng.random() < 0.04:  # unplanned downtime on ~4% of days
            hours = round(rng.uniform(4, 20), 1)
        uptime = hours / 24
        if plan.scenario == "dead" and days_left < 3:
            hours, uptime = 0.0, 0.0

        oil = max(0.0, oil * uptime)
        water = oil * wc / (1 - wc) if wc < 1 else 0.0
        records.append(
            ProductionRecord(
                date=day,
                oil_bbl=round(oil, 1),
                gas_mcf=round(oil * gor / 1000, 1),
                water_bbl=round(water, 1),
                hours_on=hours,
            )
        )
    return records


def seed(db: Session, end: date | None = None, rng_seed: int = 42) -> int:
    """Insert the demo dataset. Returns the number of wells created."""
    end = end or date.today() - timedelta(days=1)
    rng = random.Random(rng_seed)
    for plan in PLANS:
        well = Well(
            name=plan.name,
            field=plan.field,
            lift_type=plan.lift,
            status=WellStatus.shut_in if plan.scenario == "shut_in" else WellStatus.active,
            start_date=end - timedelta(days=plan.online_days_ago - 1),
        )
        well.records = generate_records(plan, end, rng)
        db.add(well)
    db.commit()
    return len(PLANS)


def seed_if_empty(db: Session) -> bool:
    if db.scalar(select(Well.id).limit(1)) is not None:
        return False
    seed(db)
    return True


if __name__ == "__main__":
    from app.database import Base, SessionLocal, engine

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        print(f"Seeded {seed(session)} wells with {HISTORY_DAYS} days of history.")
