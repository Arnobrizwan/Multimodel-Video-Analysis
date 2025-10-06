"""Integration tests for full workflow"""
import pytest
from unittest.mock import patch, Mock
from main import video_store


@pytest.mark.integration
class TestVideoProcessingWorkflow:
    """Test complete video processing workflow"""

    def test_full_workflow_process_chat_search(
        self, client, mock_youtube_transcript, mock_gemini_generate,
        mock_gemini_embed, mock_video_download, mock_visual_index
    ):
        """Test complete workflow: process video -> chat -> visual search"""

        # Step 1: Process video
        process_response = client.post("/process_video", json={
            "youtube_url": "https://www.youtube.com/watch?v=integration_test"
        })
        assert process_response.status_code == 200
        video_id = process_response.json()["video_id"]

        # Step 2: Chat with video
        with patch('main.genai.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_instance.generate_content.return_value = Mock(
                text="This covers testing. See [0:00] for details."
            )
            mock_model.return_value = mock_instance

            chat_response = client.post("/chat", json={
                "video_id": video_id,
                "question": "What is covered in this video?"
            })
            assert chat_response.status_code == 200
            assert "answer" in chat_response.json()

        # Step 3: Visual search
        visual_response = client.post("/visual_search", json={
            "video_id": video_id,
            "query": "show me code examples"
        })
        assert visual_response.status_code == 200
        assert "matches" in visual_response.json()

        # Step 4: Get video info
        info_response = client.get(f"/video/{video_id}")
        assert info_response.status_code == 200
        assert info_response.json()["video_id"] == video_id


@pytest.mark.integration
class TestCacheIntegration:
    """Test cache integration across requests"""

    def test_embedding_cache_across_requests(
        self, client, sample_video_data, mock_gemini_embed
    ):
        """Test that embeddings are cached across multiple requests"""
        video_id = "cache_test"
        video_store[video_id] = sample_video_data

        # First chat request
        with patch('main.genai.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_instance.generate_content.return_value = Mock(text="Answer 1")
            mock_model.return_value = mock_instance

            client.post("/chat", json={
                "video_id": video_id,
                "question": "What is this?"
            })

        # Check cache stats
        stats1 = client.get("/cache/stats").json()
        initial_hits = stats1["embedding_cache"]["hits"]

        # Second chat request with same question (should hit cache)
        with patch('main.genai.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_instance.generate_content.return_value = Mock(text="Answer 2")
            mock_model.return_value = mock_instance

            client.post("/chat", json={
                "video_id": video_id,
                "question": "What is this?"
            })

        # Check cache stats again
        stats2 = client.get("/cache/stats").json()
        final_hits = stats2["embedding_cache"]["hits"]

        # Should have at least one cache hit
        assert final_hits > initial_hits


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling across the application"""

    def test_invalid_video_id_cascades(self, client):
        """Test that invalid video ID errors properly across endpoints"""
        invalid_id = "nonexistent_video"

        # Chat should fail
        chat_response = client.post("/chat", json={
            "video_id": invalid_id,
            "question": "test"
        })
        assert chat_response.status_code == 404

        # Visual search should fail
        visual_response = client.post("/visual_search", json={
            "video_id": invalid_id,
            "query": "test"
        })
        assert visual_response.status_code == 404

        # Get info should fail
        info_response = client.get(f"/video/{invalid_id}")
        assert info_response.status_code == 404

    def test_malformed_requests(self, client):
        """Test handling of various malformed requests"""
        # Missing required fields
        response1 = client.post("/process_video", json={})
        assert response1.status_code == 422

        response2 = client.post("/chat", json={"video_id": "test"})
        assert response2.status_code == 422

        response3 = client.post("/visual_search", json={"query": "test"})
        assert response3.status_code == 422
