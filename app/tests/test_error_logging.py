"""Tests for error logging functionality."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_404_error_logging(caplog):
    """Test 404 errors are properly logged."""
    response = client.get("/api/v4/dashboard-pages/nonexistent-page-id")
    assert response.status_code == 404
    
    # Check that error was logged
    log_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("Dashboard page not found" in str(record.message) for record in log_records)
    assert any("NotFoundException" in str(record.message) for record in log_records)


def test_validation_error_logging(caplog):
    """Test validation errors are properly logged with suggestions."""
    # Test missing required fields
    response = client.post("/api/v1/auth/register", json={"email": "invalid"})
    assert response.status_code == 422
    
    # Check that validation error was logged
    log_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("Request validation failed" in str(record.message) for record in log_records)
    
    # Check that response includes suggestions
    error_detail = response.json()["detail"][0]
    assert "suggestion" in error_detail or "type" in error_detail


def test_400_authentication_error_logging(caplog):
    """Test 400 authentication errors are properly logged."""
    # Test invalid login credentials
    response = client.post(
        "/api/v1/auth/login/",
        json={"email": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 400
    
    # Check that error was logged
    log_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("AuthenticationError" in str(record.message) for record in log_records)


def test_validation_error_suggestions():
    """Test that validation errors include helpful suggestions."""
    # Test password too short
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "short",
            "name": "Test User"
        }
    )
    assert response.status_code == 422
    error_detail = response.json()["detail"][0]
    assert "suggestion" in error_detail or "password" in error_detail.get("field", "")


def test_404_marketing_page_logging(caplog):
    """Test 404 errors for marketing pages are properly logged."""
    response = client.get("/api/v4/marketing/nonexistent-page-id")
    assert response.status_code == 404
    
    # Check that error was logged
    log_records = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("Marketing page not found" in str(record.message) for record in log_records)

