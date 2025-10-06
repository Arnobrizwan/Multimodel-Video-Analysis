"""Pytest configuration and shared fixtures"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app, video_store, embedding_cache


@pytest.fixture(autouse=True)
def reset_state():
    """Reset global state before each test"""
    video_store.clear()
    embedding_cache.clear()
    yield
    video_store.clear()
    embedding_cache.clear()


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_gemini_embed():
    """Mock Gemini embedding API"""
    with patch('main.genai.embed_content') as mock:
        mock.return_value = {
            'embedding': {
                'values': [0.1] * 768  # Standard embedding dimension
            }
        }
        yield mock


@pytest.fixture
def mock_gemini_generate():
    """Mock Gemini content generation API"""
    with patch('main.genai.GenerativeModel') as mock_model:
        mock_instance = Mock()
        mock_instance.generate_content.return_value = Mock(
            text='{"sections": [{"title": "Test Section", "timestamp": 0, "summary": "Test summary"}]}'
        )
        mock_model.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_youtube_transcript():
    """Mock YouTube transcript API"""
    with patch('main.YouTubeTranscriptApi.get_transcript') as mock:
        mock.return_value = [
            {'text': 'Hello world', 'start': 0.0, 'duration': 2.0},
            {'text': 'This is a test', 'start': 2.0, 'duration': 3.0}
        ]
        yield mock


@pytest.fixture
def mock_video_download():
    """Mock video download"""
    with patch('main.download_youtube_video') as mock:
        mock.return_value = None
        yield mock


@pytest.fixture
def mock_visual_index():
    """Mock visual indexing"""
    with patch('main.create_visual_index') as mock:
        mock.return_value = [
            {
                'timestamp': 0.0,
                'end_timestamp': 5.0,
                'description': 'Test frame description',
                'image_base64': 'base64_encoded_image',
                'embedding': {'values': [0.2] * 768}
            }
        ]
        yield mock


@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        'video_id': 'test_video_123',
        'youtube_url': 'https://www.youtube.com/watch?v=test_video_123',
        'transcript': 'Hello world This is a test',
        'sections': [
            {
                'title': 'Introduction',
                'timestamp': 0,
                'summary': 'Opening remarks'
            }
        ],
        'chunks': [
            {
                'text': 'Hello world This is a test',
                'start': 0.0,
                'end': 5.0,
                'embedding': {'values': [0.1] * 768}
            }
        ],
        'visual_index': [
            {
                'timestamp': 0.0,
                'end_timestamp': 5.0,
                'description': 'Test frame',
                'image_base64': 'base64_test',
                'embedding': {'values': [0.2] * 768}
            }
        ]
    }
