import pytest
import json
from app.database.session_manager import DatabaseSessionManager


@pytest.fixture(scope="session")
def test_user_data():
    """Fixture to load test data from JSON file."""
    # Load the test data from JSON file
    with open("tests/data/database/user.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="session")
def test_company_data():
    """Fixture to load test data from JSON file."""
    # Load the test data from JSON file
    with open("tests/data/database/company.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="session")
def test_role_data():
    """Fixture to load test data from JSON file."""
    # Load the test data from JSON file
    with open("tests/data/database/role.json") as f:
        data = json.load(f)
    return data


@pytest.fixture(scope="function")
def test_session():
    test_configs = {
        "database_url": "sqlite:///:memory:",
        "environment": "test",
        "cor_origins": {"allowed": ["*"], "blocked": []},
        "jwt": {},
        "email": {},
        "version": "0.1.0",
        "name": "Userverse",
        "description": "Mocked config for test",
    }

    db_manager = DatabaseSessionManager(configs=test_configs)
    engine = db_manager.engine

    # Clean slate schema
    db_manager._base.metadata.create_all(bind=engine)

    session = db_manager.session_object()
    yield session
    session.close()
