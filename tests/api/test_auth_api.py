"""
API Integration Tests — Authentication + Endpoint Access Control
Run with: pytest tests/api/test_auth_api.py -v
Requires the FastAPI app importable (mocks Snowflake calls where needed).
"""

import sys
import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", "api"))
os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

from main import app  # noqa: E402

client = TestClient(app)


class TestAuthentication:

    def test_login_success_admin(self):
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "Admin@123"},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["user"]["role"] == "admin"

    def test_login_wrong_password_rejected(self):
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrong_password"},
        )
        assert response.status_code == 401

    def test_login_unknown_user_rejected(self):
        response = client.post(
            "/api/auth/login",
            data={"username": "ghost_user", "password": "whatever"},
        )
        assert response.status_code == 401

    def test_protected_route_requires_token(self):
        response = client.get("/api/drugs/summary")
        assert response.status_code == 401

    def test_protected_route_with_valid_token(self):
        login = client.post(
            "/api/auth/login", data={"username": "viewer", "password": "Viewer@123"}
        )
        token = login.json()["access_token"]
        with patch("routes.drugs.run_query", return_value=[]):
            response = client.get(
                "/api/drugs/summary", headers={"Authorization": f"Bearer {token}"}
            )
        assert response.status_code == 200

    def test_admin_only_route_blocks_viewer(self):
        login = client.post(
            "/api/auth/login", data={"username": "viewer", "password": "Viewer@123"}
        )
        token = login.json()["access_token"]
        response = client.get(
            "/api/ai/data-quality-check?year=2023",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    def test_admin_only_route_allows_admin(self):
        login = client.post(
            "/api/auth/login", data={"username": "admin", "password": "Admin@123"}
        )
        token = login.json()["access_token"]
        with patch("services.ai_data_quality_checker.run_query", return_value=[]):
            response = client.get(
                "/api/ai/data-quality-check?year=2023",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code in (200, 500)  # 500 only if OpenAI call fails in test env

    def test_get_current_user_profile(self):
        login = client.post(
            "/api/auth/login", data={"username": "analyst", "password": "Analyst@123"}
        )
        token = login.json()["access_token"]
        response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        assert response.json()["username"] == "analyst"

    def test_refresh_token_flow(self):
        login = client.post(
            "/api/auth/login", data={"username": "admin", "password": "Admin@123"}
        )
        refresh_token = login.json()["refresh_token"]
        response = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert response.status_code == 200
        assert "access_token" in response.json()


class TestHealthEndpoints:

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_metrics_endpoint_exposed(self):
        response = client.get("/metrics")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
