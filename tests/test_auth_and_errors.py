def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_missing_user_id_header_returns_401(client):
    response = client.get("/api/reports")
    assert response.status_code == 401
    payload = response.json()
    assert payload["statusCode"] == 401
    assert payload["error"] == "Unauthorized"
