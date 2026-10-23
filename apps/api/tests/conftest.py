"""All default tests run against a disposable database, never an application DB."""
import os
import tempfile
from pathlib import Path

_test_dir = tempfile.TemporaryDirectory(prefix="avadental-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "test.db")
os.environ["APP_ENV"] = "test"
os.environ["DEMO_SEED_ENABLED"] = "true"
from app.db.base import Base
from app.db.session import engine
from app.models import models
Base.metadata.create_all(engine)  # Only an isolated test database.

import pytest
from app.db.init_db import seed_demo_data
from app.db.session import SessionLocal

@pytest.fixture(autouse=True)
def isolated_state():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    seed_demo_data()
    yield
