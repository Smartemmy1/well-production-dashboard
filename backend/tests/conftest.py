"""Shared fixtures: every test gets a fresh in-memory database."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import ProductionRecord, Well


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    yield session
    session.close()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    # Not used as a context manager, so the startup seeding does not run.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def make_well(db):
    """Create a well with `days` of flat production ending yesterday."""

    def _make(name="T-01", field="Test Field", days=40, oil=1000.0, water=100.0, gas=800.0):
        end = date.today() - timedelta(days=1)
        well = Well(name=name, field=field, start_date=end - timedelta(days=days - 1))
        well.records = [
            ProductionRecord(
                date=end - timedelta(days=days - 1 - i),
                oil_bbl=oil,
                gas_mcf=gas,
                water_bbl=water,
                hours_on=24,
            )
            for i in range(days)
        ]
        db.add(well)
        db.commit()
        return well

    return _make
