import pytest
from fastapi.testclient import TestClient
from main import app, init_db

@pytest.fixture(autouse=True)
def setup_db(tmp_path, monkeypatch):
    test_db = tmp_path / "test_auth.db"
    monkeypatch.setenv("DEMO_DB_PATH", str(test_db))
    import main
    main.DB_PATH = str(test_db)
    init_db()

def test_verify_requires_token_for_remote_client():
    client = TestClient(app)
    response = client.get("/verify", headers={"X-Forwarded-For": "203.0.113.195", "X-Original-URI": "/realpeep/"})
    assert response.status_code == 401

def test_verify_permits_localhost_client_without_token():
    client = TestClient(app)
    # Direct loopback IP
    response = client.get("/verify", headers={"X-Forwarded-For": "127.0.0.1", "X-Original-URI": "/realpeep/"})
    assert response.status_code == 200
    assert response.text == "ok"

def test_verify_permits_slirp4netns_host_gateway_without_token():
    client = TestClient(app)
    # In rootless podman, host traffic arrives via 10.0.2.100 or 10.0.2.2
    response = client.get("/verify", headers={"X-Forwarded-For": "10.0.2.100", "X-Original-URI": "/realpeep/"})
    assert response.status_code == 200
    assert response.text == "ok"
