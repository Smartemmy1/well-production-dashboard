"""Unit tests for the engineering calculations and alert rules."""

from datetime import date, timedelta

import pytest

from app.config import Settings
from app.models import ProductionRecord, Well, WellStatus
from app.seed import arps_rate
from app.services.analytics import evaluate_alerts, gas_oil_ratio, water_cut

SETTINGS = Settings(seed_demo_data=False)


def records(oil_values, water=0.0, gas=0.0):
    start = date(2026, 1, 1)
    return [
        ProductionRecord(date=start + timedelta(days=i), oil_bbl=o, gas_mcf=gas, water_bbl=water)
        for i, o in enumerate(oil_values)
    ]


def well(status=WellStatus.active):
    return Well(id=1, name="T-01", field="Test", status=status, start_date=date(2026, 1, 1))


def test_water_cut():
    assert water_cut(750, 250) == 0.25
    assert water_cut(0, 0) is None


def test_gas_oil_ratio_is_in_scf_per_bbl():
    assert gas_oil_ratio(oil_bbl=1000, gas_mcf=800) == 800.0
    assert gas_oil_ratio(0, 500) is None


def test_arps_rate_declines_from_initial_rate():
    assert arps_rate(1000, 0.5, 0.5, 0) == pytest.approx(1000)
    assert arps_rate(1000, 0.5, 0.5, 365) < arps_rate(1000, 0.5, 0.5, 180) < 1000


def test_steady_well_has_no_alerts():
    assert evaluate_alerts(well(), records([1000] * 37, water=100), SETTINGS) == []


def test_drop_over_half_is_critical():
    alerts = evaluate_alerts(well(), records([1000] * 30 + [400] * 7), SETTINGS)
    assert [(a.kind, a.severity) for a in alerts] == [("production_drop", "critical")]


def test_moderate_drop_is_warning():
    alerts = evaluate_alerts(well(), records([1000] * 30 + [700] * 7), SETTINGS)
    assert [(a.kind, a.severity) for a in alerts] == [("production_drop", "warning")]


def test_high_water_cut_warns():
    alerts = evaluate_alerts(well(), records([100] * 37, water=900), SETTINGS)
    assert [a.kind for a in alerts] == ["high_water_cut"]


def test_three_zero_days_is_no_production():
    alerts = evaluate_alerts(well(), records([1000] * 34 + [0, 0, 0]), SETTINGS)
    assert [(a.kind, a.severity) for a in alerts] == [("no_production", "critical")]


def test_shut_in_wells_are_not_alerted():
    assert evaluate_alerts(well(WellStatus.shut_in), records([0] * 37), SETTINGS) == []


def test_short_history_skips_drop_check():
    assert evaluate_alerts(well(), records([1000] * 3 + [100] * 7), SETTINGS) == []
