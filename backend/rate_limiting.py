"""Rate limiting middleware to prevent abuse and DoS"""
from fastapi import HTTPException, Request
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict
import time


class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self, requests_per_minute: int = 10, requests_per_hour: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

        # Track requests by IP
        self.minute_requests: Dict[str, list] = defaultdict(list)
        self.hour_requests: Dict[str, list] = defaultdict(list)

    def _clean_old_requests(self, requests_list: list, cutoff_time: datetime):
        """Remove requests older than cutoff time"""
        return [req_time for req_time in requests_list if req_time > cutoff_time]

    def check_rate_limit(self, client_ip: str) -> None:
        """
        Check if client has exceeded rate limits.
        Raises HTTPException if limit exceeded.
        """
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        # Clean old requests
        self.minute_requests[client_ip] = self._clean_old_requests(
            self.minute_requests[client_ip], minute_ago
        )
        self.hour_requests[client_ip] = self._clean_old_requests(
            self.hour_requests[client_ip], hour_ago
        )

        # Check minute limit
        if len(self.minute_requests[client_ip]) >= self.requests_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_minute} requests per minute"
            )

        # Check hour limit
        if len(self.hour_requests[client_ip]) >= self.requests_per_hour:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {self.requests_per_hour} requests per hour"
            )

        # Record this request
        self.minute_requests[client_ip].append(now)
        self.hour_requests[client_ip].append(now)

    def get_stats(self, client_ip: str) -> Dict:
        """Get rate limit stats for client"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)

        minute_count = len([
            req for req in self.minute_requests[client_ip]
            if req > minute_ago
        ])
        hour_count = len([
            req for req in self.hour_requests[client_ip]
            if req > hour_ago
        ])

        return {
            "requests_last_minute": minute_count,
            "minute_limit": self.requests_per_minute,
            "requests_last_hour": hour_count,
            "hour_limit": self.requests_per_hour
        }


# Global rate limiter instance
rate_limiter = RateLimiter(
    requests_per_minute=20,  # 20 requests per minute
    requests_per_hour=200     # 200 requests per hour
)


async def check_rate_limit(request: Request):
    """Dependency to check rate limits"""
    client_ip = request.client.host
    rate_limiter.check_rate_limit(client_ip)
