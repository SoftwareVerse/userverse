import os
import shutil
import glob
import pytest


def test_profiling_enabled(client):
    # Ensure clean state
    if os.path.exists("profiles"):
        shutil.rmtree("profiles")
    os.makedirs("profiles")

    response = client.get("/", headers={"X-Profile": "true"})
    assert response.status_code == 200

    # Check for profile file
    files = glob.glob("profiles/*.prof")
    assert len(files) >= 1

    # Cleanup
    shutil.rmtree("profiles")


def test_profiling_disabled_by_default(client):
    # Ensure clean state
    if os.path.exists("profiles"):
        shutil.rmtree("profiles")
    os.makedirs("profiles")

    response = client.get("/")
    assert response.status_code == 200

    # Check for profile file
    files = glob.glob("profiles/*.prof")
    assert len(files) == 0

    # Cleanup
    shutil.rmtree("profiles")
