import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.exceptions import register_exception_handlers
from app.models.response_messages import ErrorResponseMessagesModel
from app.utils.app_error import AppError


@pytest.fixture
def exception_client():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-http-str")
    async def raise_http_str():
        raise HTTPException(status_code=400, detail="Bad request")

    @app.get("/raise-http-dict")
    async def raise_http_dict():
        raise HTTPException(status_code=403, detail={"reason": "forbidden"})

    @app.get("/raise-validation")
    async def raise_validation(limit: int):
        return {"limit": limit}

    @app.get("/raise-app-error")
    async def raise_app_error():
        raise AppError(
            status_code=409,
            message="Business rule violated",
            error="role_conflict",
            log_error=False,
        )

    @app.get("/raise-unhandled")
    async def raise_unhandled():
        raise RuntimeError("boom")

    @app.get("/raise-chained")
    async def raise_chained():
        try:
            raise ValueError("inner problem")
        except ValueError as exc:
            raise RuntimeError("outer problem") from exc

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


def test_not_found_handler_returns_plain_text(exception_client: TestClient):
    response = exception_client.get("/missing-endpoint")
    assert response.status_code == 404
    assert response.text == "Not found"


def test_http_exception_with_string_detail(exception_client: TestClient):
    response = exception_client.get(
        "/raise-http-str", headers={"x-correlation-id": "cid-1"}
    )

    body = response.json()
    assert response.status_code == 400
    assert body["detail"]["message"] == "Bad request"
    assert body["detail"]["code"] == "http_error"
    assert body["detail"]["correlation_id"] == "cid-1"


def test_http_exception_with_dict_detail(exception_client: TestClient):
    response = exception_client.get(
        "/raise-http-dict", headers={"x-request-id": "req-42"}
    )

    body = response.json()
    assert response.status_code == 403
    assert body["detail"]["message"] == "Request failed"
    assert body["detail"]["code"] == "http_error"
    assert body["detail"]["correlation_id"] == "req-42"
    assert body["detail"]["extra"] == {"detail": {"reason": "forbidden"}}


def test_request_validation_error_handler(exception_client: TestClient):
    response = exception_client.get("/raise-validation?limit=abc")

    body = response.json()
    assert response.status_code == 422
    assert body["detail"]["message"] == "Validation failed"
    assert body["detail"]["code"] == "validation_error"
    assert "correlation_id" in body["detail"]
    assert "errors" in body["detail"]["extra"]
    assert body["detail"]["extra"]["errors"]


def test_app_error_handler(exception_client: TestClient):
    response = exception_client.get("/raise-app-error")

    body = response.json()
    assert response.status_code == 409
    assert body["detail"]["message"] == "Business rule violated"
    assert body["detail"]["code"] == "app_error"
    assert body["detail"]["extra"] == {"error": "role_conflict"}


def test_unhandled_exception_handler_in_prod_mode(exception_client: TestClient):
    response = exception_client.get("/raise-unhandled")

    body = response.json()
    assert response.status_code == 500
    assert body["detail"]["message"] == ErrorResponseMessagesModel.GENERIC_ERROR
    assert body["detail"]["code"] == "internal_error"
    assert "correlation_id" in body["detail"]


def test_unhandled_exception_handler_in_debug_mode(
    exception_client: TestClient, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr("app.exceptions.DEBUG_ERRORS", True)
    response = exception_client.get("/raise-chained")

    body = response.json()
    assert response.status_code == 500
    assert body["detail"]["message"] == "inner problem"
    assert body["detail"]["code"] == "ValueError"
    assert body["detail"]["extra"]["exception_type"] == "ValueError"
    assert body["detail"]["extra"]["exception_message"] == "inner problem"
    assert body["detail"]["extra"]["exception_trail"] == [
        "RuntimeError",
        "ValueError",
    ]
