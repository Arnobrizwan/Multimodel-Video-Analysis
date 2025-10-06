"""Logging configuration"""
import logging
import sys
from datetime import datetime
import json
import traceback


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }

        # Add custom fields
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id

        return json.dumps(log_data)


def setup_logging(log_level: str = "INFO", structured: bool = False):
    """
    Setup application logging

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Use structured JSON logging
    """
    # Get root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper()))

    # Set formatter
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Create application logger
app_logger = logging.getLogger("video_analysis")


def log_error(
    logger: logging.Logger,
    error_type: str,
    message: str,
    exc_info: Exception = None,
    **kwargs
):
    """
    Log error with structured information

    Args:
        logger: Logger instance
        error_type: Type of error
        message: Error message
        exc_info: Exception object
        **kwargs: Additional context fields
    """
    extra = {"error_type": error_type}
    extra.update(kwargs)

    if exc_info:
        logger.error(message, exc_info=exc_info, extra=extra)
    else:
        logger.error(message, extra=extra)


def log_info(logger: logging.Logger, message: str, **kwargs):
    """Log info with structured information"""
    logger.info(message, extra=kwargs)


def log_warning(logger: logging.Logger, message: str, **kwargs):
    """Log warning with structured information"""
    logger.warning(message, extra=kwargs)
