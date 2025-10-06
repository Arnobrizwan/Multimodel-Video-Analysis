"""Custom exceptions for better error handling"""
from fastapi import HTTPException, status


class VideoAnalysisException(Exception):
    """Base exception for video analysis errors"""
    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TranscriptNotAvailableError(VideoAnalysisException):
    """Raised when video transcript is not available"""
    pass


class VideoDownloadError(VideoAnalysisException):
    """Raised when video download fails"""
    pass


class GeminiAPIError(VideoAnalysisException):
    """Raised when Gemini API call fails"""
    pass


class EmbeddingGenerationError(VideoAnalysisException):
    """Raised when embedding generation fails"""
    pass


class VideoProcessingError(VideoAnalysisException):
    """Raised when video processing fails"""
    pass


class FrameExtractionError(VideoAnalysisException):
    """Raised when frame extraction fails"""
    pass


class InvalidVideoIDError(VideoAnalysisException):
    """Raised when video ID is invalid or cannot be extracted"""
    pass


class ChunkCreationError(VideoAnalysisException):
    """Raised when chunk creation fails"""
    pass


def create_error_response(
    status_code: int,
    error_type: str,
    message: str,
    details: dict = None
) -> HTTPException:
    """
    Create standardized error response

    Args:
        status_code: HTTP status code
        error_type: Type of error (e.g., "TranscriptError", "APIError")
        message: Human-readable error message
        details: Additional error details

    Returns:
        HTTPException with structured error information
    """
    error_detail = {
        "error_type": error_type,
        "message": message,
    }

    if details:
        error_detail["details"] = details

    return HTTPException(status_code=status_code, detail=error_detail)
