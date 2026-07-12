"""
Basic smoke tests. Run with: pytest backend/tests -q
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from main import app  # noqa: E402
from app.core.database import init_db  # noqa: E402

init_db()
client = TestClient(app)


def test_health_check():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_signup_and_login():
    email = "test_user_reposage@example.com"
    resp = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "SuperSecret123!", "full_name": "Test User"},
    )
    assert resp.status_code in (200, 400)  # 400 if re-run against existing db

    resp = client.post(
        "/api/v1/auth/login", json={"email": email, "password": "SuperSecret123!"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_repo_connect_rejects_internal_urls():
    # Need auth first
    client.post(
        "/api/v1/auth/signup",
        json={"email": "internal_test@example.com", "password": "SuperSecret123!"},
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "internal_test@example.com", "password": "SuperSecret123!"},
    )
    token = login.json()["access_token"]

    resp = client.post(
        "/api/v1/repositories/connect",
        headers={"Authorization": f"Bearer {token}"},
        json={"clone_url": "https://localhost/evil/repo.git"},
    )
    assert resp.status_code == 400
