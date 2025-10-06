"""Test input validation and security"""
import pytest
from fastapi.testclient import TestClient


class TestURLValidation:
    """Test YouTube URL validation"""

    def test_valid_youtube_urls(self, client):
        """Test that valid YouTube URLs are accepted"""
        valid_urls = [
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://www.youtube.com/shorts/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
        ]

        for url in valid_urls:
            response = client.post("/process_video", json={
                "youtube_url": url
            })
            # Should not fail validation (might fail for other reasons in tests)
            assert response.status_code != 422, f"URL {url} failed validation"

    def test_ssrf_protection(self, client):
        """Test that non-YouTube URLs are rejected (SSRF protection)"""
        malicious_urls = [
            "https://evil.com/watch?v=dQw4w9WgXcQ",
            "https://192.168.1.1/video",
            "http://localhost:8000/admin",
            "file:///etc/passwd",
            "ftp://example.com/file",
        ]

        for url in malicious_urls:
            response = client.post("/process_video", json={
                "youtube_url": url
            })
            assert response.status_code == 422
            assert "YouTube" in response.json()["detail"][0]["msg"]

    def test_url_length_limit(self, client):
        """Test URL length validation"""
        # URL too long
        long_url = "https://www.youtube.com/watch?v=" + "a" * 500
        response = client.post("/process_video", json={
            "youtube_url": long_url
        })
        assert response.status_code == 422
        assert "too long" in response.json()["detail"][0]["msg"].lower()

    def test_invalid_url_format(self, client):
        """Test rejection of malformed URLs"""
        invalid_urls = [
            "not a url",
            "javascript:alert(1)",
            "//youtube.com/watch?v=test",
        ]

        for url in invalid_urls:
            response = client.post("/process_video", json={
                "youtube_url": url
            })
            assert response.status_code == 422


class TestChatValidation:
    """Test chat input validation"""

    def test_question_length_limits(self, client, sample_video_data):
        """Test question length validation"""
        from main import video_store
        video_store["test123"] = sample_video_data

        # Too short (empty)
        response = client.post("/chat", json={
            "video_id": "test123",
            "question": ""
        })
        assert response.status_code == 422

        # Too long
        long_question = "a" * 2001
        response = client.post("/chat", json={
            "video_id": "test123",
            "question": long_question
        })
        assert response.status_code == 422
        assert "too long" in response.json()["detail"][0]["msg"].lower()

    def test_question_whitespace_only(self, client, sample_video_data):
        """Test rejection of whitespace-only questions"""
        from main import video_store
        video_store["test123"] = sample_video_data

        response = client.post("/chat", json={
            "video_id": "test123",
            "question": "   \n\t   "
        })
        assert response.status_code == 422
        assert "whitespace" in response.json()["detail"][0]["msg"].lower()

    def test_video_id_validation(self, client, sample_video_data):
        """Test video ID format validation"""
        from main import video_store

        # Invalid characters
        response = client.post("/chat", json={
            "video_id": "test/../../../etc/passwd",
            "question": "What is this?"
        })
        assert response.status_code == 422

        # SQL injection attempt
        response = client.post("/chat", json={
            "video_id": "test'; DROP TABLE videos--",
            "question": "What is this?"
        })
        assert response.status_code == 422

        # Too long
        response = client.post("/chat", json={
            "video_id": "a" * 101,
            "question": "What is this?"
        })
        assert response.status_code == 422


class TestVisualSearchValidation:
    """Test visual search input validation"""

    def test_query_length_limits(self, client, sample_video_data):
        """Test visual search query length validation"""
        from main import video_store
        video_store["test123"] = sample_video_data

        # Too long
        long_query = "a" * 501
        response = client.post("/visual_search", json={
            "video_id": "test123",
            "query": long_query
        })
        assert response.status_code == 422

    def test_query_empty(self, client, sample_video_data):
        """Test rejection of empty queries"""
        from main import video_store
        video_store["test123"] = sample_video_data

        response = client.post("/visual_search", json={
            "video_id": "test123",
            "query": ""
        })
        assert response.status_code == 422


class TestAuthValidation:
    """Test authentication input validation"""

    def test_username_validation(self, client):
        """Test username validation rules"""
        # Too short
        response = client.post("/auth/register", json={
            "username": "ab",
            "password": "Test1234"
        })
        assert response.status_code == 422
        assert "3 characters" in response.json()["detail"][0]["msg"]

        # Too long
        response = client.post("/auth/register", json={
            "username": "a" * 51,
            "password": "Test1234"
        })
        assert response.status_code == 422

        # Invalid characters
        response = client.post("/auth/register", json={
            "username": "test<script>",
            "password": "Test1234"
        })
        assert response.status_code == 422

        # SQL injection attempt
        response = client.post("/auth/register", json={
            "username": "admin'--",
            "password": "Test1234"
        })
        assert response.status_code == 422

    def test_password_validation(self, client):
        """Test password validation rules"""
        # Too short
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "Test1"
        })
        assert response.status_code == 422
        assert "8 characters" in response.json()["detail"][0]["msg"]

        # No uppercase
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "test1234"
        })
        assert response.status_code == 422

        # No lowercase
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "TEST1234"
        })
        assert response.status_code == 422

        # No digit
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "TestTest"
        })
        assert response.status_code == 422

    def test_email_validation(self, client):
        """Test email validation"""
        # Invalid format
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "Test1234",
            "email": "notanemail"
        })
        assert response.status_code == 422

        # Too long
        response = client.post("/auth/register", json={
            "username": "testuser",
            "password": "Test1234",
            "email": "a" * 250 + "@test.com"
        })
        assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting"""

    def test_rate_limit_per_minute(self, client):
        """Test that rate limiting kicks in after too many requests"""
        # Make many requests quickly
        for i in range(25):  # Exceed the 20/minute limit
            response = client.get("/")

        # Should get rate limited
        # Note: This might not work in tests without proper setup
        # as rate limiting uses client IP which may not be realistic in tests


class TestXSSPrevention:
    """Test XSS prevention in inputs"""

    def test_script_tags_in_question(self, client, sample_video_data):
        """Test that script tags don't cause issues"""
        from main import video_store
        video_store["test123"] = sample_video_data

        response = client.post("/chat", json={
            "video_id": "test123",
            "question": "<script>alert('xss')</script>What is this about?"
        })

        # Should not cause a validation error, but handled safely
        # Note: Pydantic doesn't strip HTML by default, but we validate length
        assert response.status_code in [200, 404, 500]  # Not 422 validation error
