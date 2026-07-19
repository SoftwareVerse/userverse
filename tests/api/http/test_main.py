from app.api.middleware.profiling import ProfilingMiddleware
from app.configs import settings
from app.main import create_app


def test_read_main(client):
    response = client.get("/")
    assert response.status_code == 200
    json_data = response.json()
    assert "message" in json_data
    assert "name" in json_data
    assert "version" in json_data
    assert "description" in json_data
    assert "status" in json_data
    assert json_data["status"] == "ok"


def test_read_main_includes_runtime_metadata(client):
    response = client.get("/")
    json_data = response.json()

    assert "environment" in json_data
    assert "repository" in json_data
    assert "documentation" in json_data
    assert json_data["message"] == "Welcome to the Userverse backend API"


def test_metrics_endpoint_exposes_prometheus_payload(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "python_gc_objects_collected_total" in response.text


def test_profiling_middleware_disabled_by_default(monkeypatch):
    monkeypatch.delenv("ENABLE_PROFILING", raising=False)
    app = create_app()

    assert all(
        middleware.cls is not ProfilingMiddleware for middleware in app.user_middleware
    )


def test_create_app_disables_credentials_for_wildcard_cors(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ALLOWED", ["*"])
    monkeypatch.setattr(settings, "CORS_BLOCKED", [])
    app = create_app()

    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert cors_middleware.kwargs["allow_origins"] == ["*"]
    assert cors_middleware.kwargs["allow_credentials"] is False


def test_create_app_keeps_credentials_for_explicit_cors_origins(monkeypatch):
    monkeypatch.setattr(settings, "CORS_ALLOWED", ["http://localhost:3000"])
    monkeypatch.setattr(settings, "CORS_BLOCKED", [])
    app = create_app()

    cors_middleware = next(
        middleware
        for middleware in app.user_middleware
        if middleware.cls.__name__ == "CORSMiddleware"
    )

    assert cors_middleware.kwargs["allow_origins"] == ["http://localhost:3000"]
    assert cors_middleware.kwargs["allow_credentials"] is True
