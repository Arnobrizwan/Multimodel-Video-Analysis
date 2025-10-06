"""Test API endpoints"""
import pytest
from unittest.mock import patch, Mock
from main import video_store


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check_success(self, client):
        """Test health check returns healthy status"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "multimodal-video-analysis-api"
        assert "gemini_configured" in data


class TestProcessVideoEndpoint:
    """Test /process_video endpoint"""

    def test_process_video_invalid_url(self, client):
        """Test process_video with invalid URL"""
        response = client.post("/process_video", json={
            "youtube_url": "invalid_url"
        })
        assert response.status_code == 400

    def test_process_video_missing_url(self, client):
        """Test process_video without URL"""
        response = client.post("/process_video", json={})
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    def test_process_video_with_transcript(
        self, client, mock_youtube_transcript, mock_gemini_generate,
        mock_gemini_embed, mock_video_download, mock_visual_index
    ):
        """Test process_video happy path with transcript"""
        response = client.post("/process_video", json={
            "youtube_url": "https://www.youtube.com/watch?v=test123"
        })

        assert response.status_code == 200
        data = response.json()

        assert data["video_id"] == "test123"
        assert "sections" in data
        assert isinstance(data["sections"], list)
        assert "test123" in video_store

    def test_process_video_duplicate(
        self, client, mock_youtube_transcript, mock_gemini_generate,
        mock_gemini_embed, mock_video_download, mock_visual_index
    ):
        """Test processing same video twice returns cached result"""
        url = "https://www.youtube.com/watch?v=test456"

        # First request
        response1 = client.post("/process_video", json={"youtube_url": url})
        assert response1.status_code == 200

        # Second request should return cached
        response2 = client.post("/process_video", json={"youtube_url": url})
        assert response2.status_code == 200
        assert response1.json() == response2.json()


class TestChatEndpoint:
    """Test /chat endpoint"""

    def test_chat_video_not_found(self, client):
        """Test chat with non-existent video"""
        response = client.post("/chat", json={
            "video_id": "nonexistent",
            "question": "What is this about?"
        })
        assert response.status_code == 404

    def test_chat_missing_question(self, client, sample_video_data):
        """Test chat without question"""
        video_store["test123"] = sample_video_data

        response = client.post("/chat", json={
            "video_id": "test123"
        })
        assert response.status_code == 422  # Validation error

    def test_chat_success(self, client, sample_video_data, mock_gemini_embed):
        """Test successful chat interaction"""
        video_id = "test123"
        video_store[video_id] = sample_video_data

        with patch('main.genai.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_instance.generate_content.return_value = Mock(
                text="This video is about testing. Relevant at [0:00]."
            )
            mock_model.return_value = mock_instance

            response = client.post("/chat", json={
                "video_id": video_id,
                "question": "What is this video about?"
            })

            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "relevant_timestamps" in data
            assert isinstance(data["relevant_timestamps"], list)

    def test_chat_no_chunks(self, client):
        """Test chat with video that has no chunks"""
        video_store["test123"] = {
            "video_id": "test123",
            "chunks": []
        }

        response = client.post("/chat", json={
            "video_id": "test123",
            "question": "What is this about?"
        })
        assert response.status_code == 400


class TestVisualSearchEndpoint:
    """Test /visual_search endpoint"""

    def test_visual_search_video_not_found(self, client):
        """Test visual search with non-existent video"""
        response = client.post("/visual_search", json={
            "video_id": "nonexistent",
            "query": "show me charts"
        })
        assert response.status_code == 404

    def test_visual_search_missing_query(self, client, sample_video_data):
        """Test visual search without query"""
        video_store["test123"] = sample_video_data

        response = client.post("/visual_search", json={
            "video_id": "test123"
        })
        assert response.status_code == 422  # Validation error

    def test_visual_search_success(self, client, sample_video_data, mock_gemini_embed):
        """Test successful visual search"""
        video_id = "test123"
        video_store[video_id] = sample_video_data

        response = client.post("/visual_search", json={
            "video_id": video_id,
            "query": "show me charts"
        })

        assert response.status_code == 200
        data = response.json()
        assert "matches" in data
        assert isinstance(data["matches"], list)

    def test_visual_search_no_visual_index(self, client):
        """Test visual search with video that has no visual index"""
        video_store["test123"] = {
            "video_id": "test123",
            "visual_index": []
        }

        response = client.post("/visual_search", json={
            "video_id": "test123",
            "query": "show me charts"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["matches"] == []


class TestVideoInfoEndpoint:
    """Test /video/{video_id} endpoint"""

    def test_get_video_info_not_found(self, client):
        """Test getting info for non-existent video"""
        response = client.get("/video/nonexistent")
        assert response.status_code == 404

    def test_get_video_info_success(self, client, sample_video_data):
        """Test getting video info"""
        video_id = "test123"
        video_store[video_id] = sample_video_data

        response = client.get(f"/video/{video_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["video_id"] == video_id
        assert "sections" in data
        assert "transcript_length" in data
        assert "visual_frames_indexed" in data


class TestCacheEndpoints:
    """Test cache management endpoints"""

    def test_cache_stats(self, client):
        """Test cache stats endpoint"""
        response = client.get("/cache/stats")
        assert response.status_code == 200
        data = response.json()
        assert "embedding_cache" in data
        assert "videos_cached" in data

    def test_cache_clear(self, client):
        """Test cache clear endpoint"""
        response = client.post("/cache/clear")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestRootEndpoint:
    """Test root endpoint"""

    def test_root(self, client):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "name" in data
