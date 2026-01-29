"""API end-to-end tests."""

import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.api.auth import create_access_token

client = TestClient(app)


class TestAPIEndpoints:
    """Test cases for API endpoints."""

    def setup_method(self):
        """Setup test client with authentication token."""
        token = create_access_token(data={"sub": "test_user"})
        self.headers = {"Authorization": f"Bearer {token}"}

    def test_root_endpoint(self):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "China Stock Proxy Service"
        assert data["status"] == "running"
        assert "docs" in data["endpoints"]

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "china-stock-proxy"

    def test_authentication_login(self):
        """Test authentication login endpoint."""
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "admin"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_authentication_verify(self):
        """Test token verification endpoint."""
        response = client.get(
            "/api/v1/auth/verify",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "test_user"
        assert data["valid"] is True

    def test_get_stock_list_unauthorized(self):
        """Test stock list endpoint without authentication."""
        response = client.get("/api/v1/stocks/list")
        assert response.status_code == 401

    def test_get_stock_list_authorized(self):
        """Test stock list endpoint with authentication."""
        response = client.get(
            "/api/v1/stocks/list",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "stocks" in data
        assert isinstance(data["stocks"], list)

    def test_get_stock_list_pagination(self):
        """Test stock list pagination."""
        response = client.get(
            "/api/v1/stocks/list?skip=0&limit=10",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["skip"] == 0
        assert data["limit"] == 10
        assert len(data["stocks"]) <= 10

    def test_get_daily_quotes_unauthorized(self):
        """Test daily quotes endpoint without authentication."""
        response = client.get("/api/v1/stocks/daily")
        assert response.status_code == 401

    def test_get_daily_quotes_authorized(self):
        """Test daily quotes endpoint with authentication."""
        response = client.get(
            "/api/v1/stocks/daily",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "data" in data

    def test_get_daily_quotes_with_filters(self):
        """Test daily quotes with date filters."""
        response = client.get(
            "/api/v1/stocks/daily?start_date=2024-01-01&end_date=2024-01-31",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_trigger_update_unauthorized(self):
        """Test trigger update endpoint without authentication."""
        response = client.get("/api/v1/stocks/trigger-update")
        assert response.status_code == 401

    def test_trigger_update_authorized(self):
        """Test trigger update endpoint with authentication."""
        response = client.get(
            "/api/v1/stocks/trigger-update",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "task_id" in data

    def test_trigger_update_with_stocks(self):
        """Test trigger update with specific stocks."""
        response = client.get(
            "/api/v1/stocks/trigger-update?stock_codes=000001,000002",
            headers=self.headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "000001" in str(data["stock_codes"])

    def test_invalid_authentication(self):
        """Test with invalid authentication token."""
        response = client.get(
            "/api/v1/stocks/list",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401

    def test_metrics_endpoint(self):
        """Test Prometheus metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        metrics = response.text
        assert "HELP" in metrics or "TYPE" in metrics
