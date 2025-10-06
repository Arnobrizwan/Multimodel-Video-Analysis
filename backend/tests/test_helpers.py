"""Test helper functions"""
import pytest
import numpy as np
from main import (
    embedding_to_array,
    extract_video_id,
    parse_json_from_response,
    cosine_similarity,
    create_chunks,
    EmbeddingCache
)


class TestEmbeddingToArray:
    """Test embedding_to_array function"""

    def test_none_embedding(self):
        """Test with None embedding"""
        result = embedding_to_array(None)
        assert isinstance(result, np.ndarray)
        assert result.size == 0

    def test_dict_embedding(self):
        """Test with dict embedding"""
        embedding = {'values': [0.1, 0.2, 0.3]}
        result = embedding_to_array(embedding)
        assert isinstance(result, np.ndarray)
        assert len(result) == 3
        assert np.allclose(result, [0.1, 0.2, 0.3])

    def test_list_embedding(self):
        """Test with list embedding"""
        embedding = [0.1, 0.2, 0.3]
        result = embedding_to_array(embedding)
        assert isinstance(result, np.ndarray)
        assert len(result) == 3

    def test_empty_dict_embedding(self):
        """Test with empty dict"""
        embedding = {'values': []}
        result = embedding_to_array(embedding)
        assert isinstance(result, np.ndarray)
        assert result.size == 0


class TestExtractVideoId:
    """Test extract_video_id function"""

    def test_standard_youtube_url(self):
        """Test standard youtube.com/watch?v= URL"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_short_youtube_url(self):
        """Test youtu.be short URL"""
        url = "https://youtu.be/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_youtube_shorts_url(self):
        """Test YouTube Shorts URL"""
        url = "https://www.youtube.com/shorts/dQw4w9WgXcQ"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_url_with_timestamp(self):
        """Test URL with timestamp parameter"""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
        assert extract_video_id(url) == "dQw4w9WgXcQ"

    def test_invalid_url(self):
        """Test invalid URL"""
        with pytest.raises(ValueError):
            extract_video_id("https://example.com/video")

    def test_malformed_url(self):
        """Test malformed URL"""
        with pytest.raises(ValueError):
            extract_video_id("not a url")


class TestParseJsonFromResponse:
    """Test parse_json_from_response function"""

    def test_valid_json(self):
        """Test parsing valid JSON"""
        text = '{"sections": [{"title": "Test", "timestamp": 0}]}'
        result = parse_json_from_response(text)
        assert "sections" in result
        assert len(result["sections"]) == 1

    def test_json_with_markdown(self):
        """Test JSON wrapped in markdown code blocks"""
        text = '```json\n{"sections": [{"title": "Test"}]}\n```'
        result = parse_json_from_response(text)
        assert "sections" in result

    def test_json_with_text_before(self):
        """Test JSON with explanatory text before"""
        text = 'Here is the response:\n{"sections": [{"title": "Test"}]}'
        result = parse_json_from_response(text)
        assert "sections" in result

    def test_invalid_json(self):
        """Test with invalid JSON"""
        text = 'This is not JSON'
        with pytest.raises(ValueError):
            parse_json_from_response(text)


class TestCosineSimilarity:
    """Test cosine_similarity function"""

    def test_identical_vectors(self):
        """Test cosine similarity of identical vectors"""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([1.0, 2.0, 3.0])
        similarity = cosine_similarity(a, b)
        assert np.isclose(similarity, 1.0)

    def test_orthogonal_vectors(self):
        """Test cosine similarity of orthogonal vectors"""
        a = np.array([1.0, 0.0])
        b = np.array([0.0, 1.0])
        similarity = cosine_similarity(a, b)
        assert np.isclose(similarity, 0.0)

    def test_opposite_vectors(self):
        """Test cosine similarity of opposite vectors"""
        a = np.array([1.0, 2.0, 3.0])
        b = np.array([-1.0, -2.0, -3.0])
        similarity = cosine_similarity(a, b)
        assert np.isclose(similarity, -1.0)

    def test_zero_vector(self):
        """Test with zero vector"""
        a = np.array([0.0, 0.0])
        b = np.array([1.0, 2.0])
        similarity = cosine_similarity(a, b)
        assert similarity == 0.0


class TestCreateChunks:
    """Test create_chunks function"""

    def test_create_chunks_basic(self):
        """Test basic chunk creation"""
        transcript = "Hello world. This is a test. Another sentence."
        chunks = create_chunks(transcript, chunk_size=20)

        assert len(chunks) > 0
        for chunk in chunks:
            assert 'text' in chunk
            assert 'start' in chunk
            assert 'end' in chunk

    def test_empty_transcript(self):
        """Test with empty transcript"""
        transcript = ""
        chunks = create_chunks(transcript)
        assert len(chunks) == 0

    def test_chunk_size_respected(self):
        """Test that chunks respect size limit"""
        transcript = "word " * 100  # Long transcript
        chunk_size = 50
        chunks = create_chunks(transcript, chunk_size=chunk_size)

        for chunk in chunks:
            assert len(chunk['text']) <= chunk_size * 2  # Allow some overflow


class TestEmbeddingCache:
    """Test EmbeddingCache class"""

    def test_cache_init(self):
        """Test cache initialization"""
        cache = EmbeddingCache(maxsize=10)
        assert cache.maxsize == 10
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_set_get(self):
        """Test setting and getting from cache"""
        cache = EmbeddingCache()
        embedding = {'values': [0.1, 0.2, 0.3]}

        # Set
        cache.set("test content", "retrieval_query", embedding)

        # Get
        result = cache.get("test content", "retrieval_query")
        assert result == embedding
        assert cache.hits == 1
        assert cache.misses == 0

    def test_cache_miss(self):
        """Test cache miss"""
        cache = EmbeddingCache()
        result = cache.get("nonexistent", "retrieval_query")
        assert result is None
        assert cache.misses == 1

    def test_cache_maxsize(self):
        """Test cache evicts oldest when full"""
        cache = EmbeddingCache(maxsize=2)

        # Add 3 items
        cache.set("item1", "task", {'values': [1]})
        cache.set("item2", "task", {'values': [2]})
        cache.set("item3", "task", {'values': [3]})

        # item1 should be evicted
        assert cache.get("item1", "task") is None
        assert cache.get("item2", "task") is not None
        assert cache.get("item3", "task") is not None

    def test_cache_stats(self):
        """Test cache statistics"""
        cache = EmbeddingCache()
        cache.set("test", "task", {'values': [1]})
        cache.get("test", "task")  # hit
        cache.get("missing", "task")  # miss

        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert "hit_rate" in stats

    def test_cache_clear(self):
        """Test cache clearing"""
        cache = EmbeddingCache()
        cache.set("test", "task", {'values': [1]})
        cache.get("test", "task")

        cache.clear()

        assert len(cache.cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0

    def test_cache_different_task_types(self):
        """Test that different task types create different cache entries"""
        cache = EmbeddingCache()
        content = "same content"

        cache.set(content, "retrieval_query", {'values': [1]})
        cache.set(content, "retrieval_document", {'values': [2]})

        query_result = cache.get(content, "retrieval_query")
        doc_result = cache.get(content, "retrieval_document")

        assert query_result != doc_result
        assert query_result['values'] == [1]
        assert doc_result['values'] == [2]
