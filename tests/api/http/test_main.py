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
