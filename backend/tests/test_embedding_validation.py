"""Test embedding count validation"""
import pytest
from unittest.mock import patch, Mock
from fastapi import HTTPException
import numpy as np


class TestEmbeddingCountValidation:
    """Test validation of embedding counts against chunk/frame counts"""

    def test_chunk_embedding_count_match(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test successful case where embedding count matches chunk count"""
        # Mock embeddings that match chunk count
        with patch('main.genai.embed_content') as mock_embed:
            mock_embed.return_value = {
                'embedding': [
                    {'values': [0.1] * 768},
                    {'values': [0.2] * 768}
                ]
            }

            with patch('main.create_visual_index') as mock_visual:
                mock_visual.return_value = []

                response = client.post("/process_video", json={
                    "youtube_url": "https://www.youtube.com/watch?v=test123"
                })

                # Should succeed
                assert response.status_code == 200

    def test_chunk_embedding_count_mismatch(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test error when embedding count doesn't match chunk count"""
        # Mock embeddings with wrong count
        with patch('main.genai.embed_content') as mock_embed:
            # Return only 1 embedding when we expect 2 chunks
            mock_embed.return_value = {
                'embedding': [
                    {'values': [0.1] * 768}
                    # Missing second embedding!
                ]
            }

            with patch('main.create_visual_index') as mock_visual:
                mock_visual.return_value = []

                response = client.post("/process_video", json={
                    "youtube_url": "https://www.youtube.com/watch?v=test_mismatch"
                })

                # Should fail with 500
                assert response.status_code == 500
                assert "mismatch" in response.json()["detail"].lower()

    def test_empty_embedding_detected(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test detection of empty embeddings"""
        with patch('main.genai.embed_content') as mock_embed:
            # Return embeddings with one empty
            mock_embed.return_value = {
                'embedding': [
                    {'values': [0.1] * 768},
                    {'values': []}  # Empty embedding!
                ]
            }

            with patch('main.create_visual_index') as mock_visual:
                mock_visual.return_value = []

                response = client.post("/process_video", json={
                    "youtube_url": "https://www.youtube.com/watch?v=empty_embed"
                })

                # Should fail
                assert response.status_code == 500

    def test_visual_index_embedding_mismatch(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test visual index embedding count validation"""
        from main import build_visual_index

        frames = [
            {'timestamp': 0, 'image_base64': 'base64data1'},
            {'timestamp': 5, 'image_base64': 'base64data2'},
            {'timestamp': 10, 'image_base64': 'base64data3'}
        ]

        with patch('main.genai.GenerativeModel') as mock_model:
            mock_instance = Mock()
            mock_instance.generate_content.return_value = Mock(text="Frame description")
            mock_model.return_value = mock_instance

            with patch('main.genai.embed_content') as mock_embed:
                # Return wrong number of embeddings
                mock_embed.return_value = {
                    'embedding': [
                        {'values': [0.1] * 768},
                        {'values': [0.2] * 768}
                        # Missing third embedding!
                    ]
                }

                # Should raise ValueError
                with pytest.raises(ValueError) as exc_info:
                    build_visual_index(frames)

                assert "mismatch" in str(exc_info.value).lower()

    def test_single_chunk_single_embedding(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test edge case with single chunk and single embedding"""
        with patch('main.YouTubeTranscriptApi.get_transcript') as mock_transcript:
            # Very short transcript = 1 chunk
            mock_transcript.return_value = [
                {'text': 'Short video', 'start': 0.0, 'duration': 2.0}
            ]

            with patch('main.genai.embed_content') as mock_embed:
                # Single embedding as dict (not list)
                mock_embed.return_value = {
                    'embedding': {'values': [0.1] * 768}
                }

                with patch('main.create_visual_index') as mock_visual:
                    mock_visual.return_value = []

                    response = client.post("/process_video", json={
                        "youtube_url": "https://www.youtube.com/watch?v=single_chunk"
                    })

                    # Should succeed
                    assert response.status_code == 200

    def test_index_out_of_bounds_handling(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download):
        """Test handling of IndexError during embedding mapping"""
        with patch('main.genai.embed_content') as mock_embed:
            # Create a scenario where embeddings list is shorter
            embeddings_list = [{'values': [0.1] * 768}]

            def side_effect(*args, **kwargs):
                return {'embedding': embeddings_list}

            mock_embed.side_effect = side_effect

            with patch('main.create_visual_index') as mock_visual:
                mock_visual.return_value = []

                response = client.post("/process_video", json={
                    "youtube_url": "https://www.youtube.com/watch?v=index_error"
                })

                # Should fail gracefully
                assert response.status_code == 500


class TestEmbeddingValidationLogging:
    """Test that validation errors are properly logged"""

    def test_error_logging_includes_context(self, client, mock_youtube_transcript, mock_gemini_generate, mock_video_download, caplog):
        """Test that error messages include diagnostic context"""
        with patch('main.genai.embed_content') as mock_embed:
            mock_embed.return_value = {
                'embedding': [{'values': [0.1] * 768}]  # Only 1 when expecting 2
            }

            with patch('main.create_visual_index') as mock_visual:
                mock_visual.return_value = []

                response = client.post("/process_video", json={
                    "youtube_url": "https://www.youtube.com/watch?v=logging_test"
                })

                # Check error message has context
                error_detail = response.json()["detail"]
                assert "chunks" in error_detail.lower()
                assert "embeddings" in error_detail.lower()
                # Should mention actual counts
                assert any(char.isdigit() for char in error_detail)
