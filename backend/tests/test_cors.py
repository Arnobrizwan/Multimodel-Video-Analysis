"""Test CORS configuration"""
import pytest
from fastapi.testclient import TestClient
import os


class TestCORSConfiguration:
    """Test CORS security configuration"""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-credentials" in response.headers

    def test_localhost_allowed_in_dev(self, client):
        """Test that localhost is allowed in development mode"""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:5173"}
        )

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") in [
            "http://localhost:5173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000"
        ]

    def test_credentials_allowed(self, client):
        """Test that credentials are allowed"""
        response = client.get(
            "/",
            headers={"Origin": "http://localhost:5173"}
        )

        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_specific_methods_allowed(self, client):
        """Test that only specific methods are allowed"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST"
            }
        )

        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "GET" in allowed_methods
        assert "POST" in allowed_methods
        assert "DELETE" in allowed_methods
        # Should NOT allow all methods
        assert "*" not in allowed_methods

    def test_specific_headers_allowed(self, client):
        """Test that only specific headers are allowed"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )

        allowed_headers = response.headers.get("access-control-allow-headers", "")
        assert "Content-Type" in allowed_headers or "content-type" in allowed_headers
        assert "Authorization" in allowed_headers or "authorization" in allowed_headers


class TestCORSProduction:
    """Test CORS configuration in production mode"""

    def test_production_origins_from_env(self, monkeypatch):
        """Test that production origins are loaded from environment"""
        # Set production origin
        monkeypatch.setenv("CORS_ORIGINS", "https://myapp.com,https://www.myapp.com")

        # Reload the module to pick up new env var
        import importlib
        import main
        importlib.reload(main)

        from main import allowed_origins

        assert "https://myapp.com" in allowed_origins
        assert "https://www.myapp.com" in allowed_origins
        # Should NOT allow localhost in production
        assert "http://localhost:5173" not in allowed_origins

    def test_wildcard_not_allowed(self):
        """Test that wildcard origins are never used"""
        import main
        assert "*" not in main.allowed_origins


class TestCORSPreflight:
    """Test CORS preflight requests"""

    def test_preflight_options_request(self, client):
        """Test that OPTIONS requests work for CORS preflight"""
        response = client.options(
            "/process_video",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type,Authorization"
            }
        )

        # Preflight should succeed
        assert response.status_code in [200, 204]
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

    def test_max_age_set(self, client):
        """Test that max-age is set for preflight caching"""
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # Should have max-age header to cache preflight
        max_age = response.headers.get("access-control-max-age")
        assert max_age is not None
        assert int(max_age) > 0


class TestCORSSecurity:
    """Test CORS security properties"""

    def test_no_wildcard_with_credentials(self):
        """Test that wildcard origin is not used with credentials"""
        import main

        # CRITICAL: Should NEVER have both allow_origins=['*'] and allow_credentials=True
        # This is a major security vulnerability
        assert main.allowed_origins != ["*"]

    def test_https_in_production_origins(self, monkeypatch):
        """Test that production origins use HTTPS"""
        monkeypatch.setenv("CORS_ORIGINS", "https://secure.com")

        import importlib
        import main
        importlib.reload(main)

        from main import allowed_origins

        for origin in allowed_origins:
            if "localhost" not in origin and "127.0.0.1" not in origin:
                # Production origins should use HTTPS
                assert origin.startswith("https://")

    def test_origin_validation(self, client):
        """Test that invalid origins are rejected"""
        # Request from untrusted origin
        response = client.get(
            "/",
            headers={"Origin": "https://evil.com"}
        )

        # Origin should NOT be in allowed list
        allowed_origin = response.headers.get("access-control-allow-origin")
        assert allowed_origin != "https://evil.com"
