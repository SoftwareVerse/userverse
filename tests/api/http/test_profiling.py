import os
import shutil
import glob

from fastapi.testclient import TestClient

from app.main import create_app
from app.configs import settings


def _clean_profiles_dir():
    if os.path.exists("profiles"):
        shutil.rmtree("profiles")
    os.makedirs("profiles")


def test_profiling_enabled(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_PROFILING", True)
    monkeypatch.setattr(settings, "TESTING", False)
    _clean_profiles_dir()

    with TestClient(create_app()) as client:
        response = client.get("/", headers={"X-Profile": "true"})

    assert response.status_code == 200
    assert len(glob.glob("profiles/*.prof")) >= 1
    shutil.rmtree("profiles")


def test_profiling_disabled_by_default(client):
    _clean_profiles_dir()

    response = client.get("/")
    assert response.status_code == 200

    assert len(glob.glob("profiles/*.prof")) == 0
    shutil.rmtree("profiles")
