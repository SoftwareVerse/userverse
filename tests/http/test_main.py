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
