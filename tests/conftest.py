"""
Shared pytest fixtures.

The app hard-requires a DATABASE_URL and only supports PostgreSQL in
production (see app/backend/database.py). For tests we point it at a
throwaway SQLite file instead, so the suite runs without a real Postgres
server and never touches the real dev database. This env var must be set
*before* anything under `app` is imported, since app/backend/database.py
creates the SQLAlchemy engine at import time.
"""

import os
import tempfile
from pathlib import Path

_TEST_DB_PATH = Path(tempfile.gettempdir()) / "infotainment_analyzer_test.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH.as_posix()}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.backend.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import CarModel, InfotainmentSpec, Manufacturer, OSType  # noqa: E402

Base.metadata.create_all(bind=engine)


DEFAULT_SPEC = dict(
    os_type=OSType.LINUX_PROPRIETARY,
    display_size_in=12.0,
    display_resolution_px="1920x1080",
    physical_buttons_count=2,
    voice_control=True,
    ota_updates=True,
    carplay_support=True,
    android_auto_support=True,
    personalization_profiles=True,
    builtin_navigation=True,
    smart_home_compat=False,
    multimodal_input=True,
    multi_zone_displays=False,
    multi_bluetooth=True,
    charging_route_integration=False,
    startup_time_sec=6.0,
    reaction_time_ms=100.0,
    avg_steps_to_task=3.0,
    ease_of_use_score=7.5,
    ergonomics_score=7.0,
    safety_distraction_score=6.5,
)


def make_spec(**overrides) -> dict:
    """A fully-populated InfotainmentSpec kwarg dict (minus car_model_id)."""
    spec = dict(DEFAULT_SPEC)
    spec.update(overrides)
    return spec


@pytest.fixture(autouse=True)
def _clean_db():
    """Ensure every test starts with an empty database."""
    yield
    db = SessionLocal()
    try:
        db.query(InfotainmentSpec).delete()
        db.query(CarModel).delete()
        db.query(Manufacturer).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def seed_two_cars(db_session):
    """
    Two cars with deliberately contrasting specs:
    - FastModel: bigger/quicker/easier display, no CarPlay/Android Auto, no buttons.
    - SlowModel: smaller/slower/harder display, has CarPlay/Android Auto and buttons.
    Useful both for "does ranking order make sense" and "do hard filters work".
    """
    mfr = Manufacturer(name="TestMake", country="Testland")
    db_session.add(mfr)
    db_session.flush()

    fast_car = CarModel(manufacturer_id=mfr.id, name="FastModel", model_year=2024, powertrain="BEV")
    db_session.add(fast_car)
    db_session.flush()
    db_session.add(InfotainmentSpec(car_model_id=fast_car.id, **make_spec(
        display_size_in=15.0, startup_time_sec=3.0, reaction_time_ms=50.0,
        avg_steps_to_task=2.0, ease_of_use_score=9.0, ergonomics_score=9.0,
        safety_distraction_score=8.5, physical_buttons_count=0,
        carplay_support=False, android_auto_support=False,
    )))

    slow_car = CarModel(manufacturer_id=mfr.id, name="SlowModel", model_year=2023, powertrain="ICE")
    db_session.add(slow_car)
    db_session.flush()
    db_session.add(InfotainmentSpec(car_model_id=slow_car.id, **make_spec(
        display_size_in=8.0, startup_time_sec=12.0, reaction_time_ms=250.0,
        avg_steps_to_task=5.0, ease_of_use_score=4.0, ergonomics_score=4.0,
        safety_distraction_score=3.0, physical_buttons_count=6,
        carplay_support=True, android_auto_support=True,
    )))

    db_session.commit()
    return {"fast_car_id": fast_car.id, "slow_car_id": slow_car.id}


@pytest.fixture
def seed_many_cars(db_session):
    """12 cars with strictly increasing ease_of_use_score, for limit/pagination tests."""
    mfr = Manufacturer(name="BulkMake", country="Testland")
    db_session.add(mfr)
    db_session.flush()

    ids = []
    for i in range(12):
        car = CarModel(manufacturer_id=mfr.id, name=f"Model{i}", model_year=2024, powertrain="BEV")
        db_session.add(car)
        db_session.flush()
        db_session.add(InfotainmentSpec(car_model_id=car.id, **make_spec(ease_of_use_score=float(i))))
        ids.append(car.id)

    db_session.commit()
    return ids


@pytest.fixture
def seed_car_without_spec(db_session):
    """A car with no InfotainmentSpec row - must be ignored by ranking/filters."""
    mfr = Manufacturer(name="SpecLessMake", country="Testland")
    db_session.add(mfr)
    db_session.flush()
    car = CarModel(manufacturer_id=mfr.id, name="NoSpecModel", model_year=2024, powertrain="BEV")
    db_session.add(car)
    db_session.commit()
    return car.id
