from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import tomllib


@lru_cache(maxsize=1)
def load_project_defaults(project_root: Path) -> dict[str, str | None]:
    defaults: dict[str, str | None] = {
        "name": "Userverse",
        "version": "0.1.0",
        "description": "Userverse backend API",
        "repository": None,
        "documentation": None,
    }
    pyproject_path = project_root / "pyproject.toml"
    try:
        with pyproject_path.open("rb") as file:
            project = tomllib.load(file).get("project", {})
    except (FileNotFoundError, OSError, tomllib.TOMLDecodeError):
        return defaults

    project_urls = project.get("urls") or {}
    normalized_urls = {
        str(key).lower(): str(value) for key, value in project_urls.items()
    }
    return {
        "name": str(project.get("name") or defaults["name"]),
        "version": str(project.get("version") or defaults["version"]),
        "description": str(project.get("description") or defaults["description"]),
        "repository": normalized_urls.get("repository", defaults["repository"]),
        "documentation": normalized_urls.get(
            "documentation", defaults["documentation"]
        ),
    }
