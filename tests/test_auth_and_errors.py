def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_register_and_login(client):
    register_response = client.post(
        "/api/auth/register",
        json={"email": "test@example.com", "password": "secret123", "full_name": "Test User"},
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    assert "token" in register_payload
    assert register_payload["user"]["email"] == "test@example.com"

    login_response = client.post("/api/auth/login", json={"email": "test@example.com", "password": "secret123"})
    assert login_response.status_code == 200
    login_payload = login_response.json()
    assert "token" in login_payload


def test_error_envelope_on_invalid_login(client):
    response = client.post("/api/auth/login", json={"email": "missing@example.com", "password": "bad"})
    assert response.status_code == 401
    payload = response.json()
    assert "error" in payload
    assert payload["error"]["code"] == "HTTP_ERROR"
