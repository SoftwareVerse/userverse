import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base

# Import model modules so SQLAlchemy metadata is fully registered.
from app.database import association_user_company  # noqa: F401
from app.database import company  # noqa: F401
from app.database import role  # noqa: F401
from app.database import user  # noqa: F401


@pytest.fixture
def test_session():
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def test_user_data():
    with open("tests/data/database/user.json", encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(scope="session")
def test_company_data():
    with open("tests/data/database/company.json", encoding="utf-8") as file:
        return json.load(file)


@pytest.fixture(scope="session")
def test_role_data():
    with open("tests/data/database/role.json", encoding="utf-8") as file:
        return json.load(file)
