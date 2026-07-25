import os
import shutil
import glob

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.configs import settings

pytestmark = pytest.mark.anyio


def _clean_profiles_dir():
    if os.path.exists("profiles"):
        shutil.rmtree("profiles")
    os.makedirs("profiles")


async def test_profiling_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PROFILING", True)
    monkeypatch.setattr(settings, "TESTING", False)
    _clean_profiles_dir()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/", headers={"X-Profile": "true"})

    assert response.status_code == 200
    assert len(glob.glob("profiles/*.prof")) >= 1
    shutil.rmtree("profiles")


async def test_profiling_disabled_by_default(client):
    _clean_profiles_dir()

    response = await client.get("/")
    assert response.status_code == 200

    assert len(glob.glob("profiles/*.prof")) == 0
    shutil.rmtree("profiles")
