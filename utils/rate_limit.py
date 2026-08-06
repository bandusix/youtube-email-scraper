#!/usr/bin/env python3
"""
Rate limiting utilities for YouTube Email Scraper.

Implements per-domain rate limiting to avoid being blocked.
"""

import time
from collections import defaultdict
from typing import Dict, Optional
import threading


class RateLimiter:
    """
    Per-domain rate limiter with exponential backoff on rate limit errors.

    Thread-safe implementation that tracks request timestamps per domain
    and enforces minimum delay between requests.
    """

    def __init__(self, requests_per_second: float = 1.0, burst: int = 3):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second per domain
            burst: Allow short bursts of this many requests
        """
        self.min_interval = 1.0 / requests_per_second
        self.burst = burst

        self.last_request: Dict[str, float] = {}
        self.request_counts: Dict[str, int] = defaultdict(int)
        self.backoff_until: Dict[str, float] = {}

        self._lock = threading.Lock()

    def wait(self, domain: str) -> None:
        """
        Wait if necessary to respect rate limit for this domain.

        Args:
            domain: Domain name to rate limit
        """
        with self._lock:
            now = time.time()

            # Check if we're in backoff period
            if domain in self.backoff_until:
                backoff_end = self.backoff_until[domain]
                if now < backoff_end:
                    wait_time = backoff_end - now
                    time.sleep(wait_time)
                    now = time.time()
                else:
                    # Backoff period ended
                    del self.backoff_until[domain]
                    self.request_counts[domain] = 0

            # Check normal rate limit
            if domain in self.last_request:
                elapsed = now - self.last_request[domain]
                if elapsed < self.min_interval:
                    time.sleep(self.min_interval - elapsed)
                    now = time.time()

            self.last_request[domain] = now
            self.request_counts[domain] += 1

    def report_rate_limit(self, domain: str, retry_after: Optional[int] = None) -> None:
        """
        Report that we hit a rate limit (HTTP 429) for this domain.

        Args:
            domain: Domain that rate limited us
            retry_after: Retry-After header value in seconds
        """
        with self._lock:
            # Exponential backoff: start with 60s, double each time
            current_backoff = 60
            if domain in self.backoff_until:
                # Already in backoff, double the time
                prev_backoff = self.backoff_until[domain] - time.time()
                current_backoff = max(prev_backoff * 2, 60)

            if retry_after:
                # Use server's suggestion if provided
                current_backoff = max(retry_after, current_backoff)

            # Cap at 30 minutes
            current_backoff = min(current_backoff, 1800)

            self.backoff_until[domain] = time.time() + current_backoff

    def get_stats(self) -> Dict[str, Dict]:
        """Get rate limiting statistics."""
        with self._lock:
            now = time.time()
            stats = {}

            for domain in set(self.last_request.keys()) | set(self.backoff_until.keys()):
                stats[domain] = {
                    'request_count': self.request_counts.get(domain, 0),
                    'last_request': self.last_request.get(domain),
                    'in_backoff': domain in self.backoff_until,
                    'backoff_remaining': max(0, self.backoff_until.get(domain, 0) - now),
                }

            return stats


class UserAgentRotator:
    """
    Rotate User-Agent headers to appear more like regular browser traffic.
    """

    # Common user agents for major browsers
    USER_AGENTS = [
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]

    def __init__(self):
        self.index = 0
        self._lock = threading.Lock()

    def get_next(self) -> str:
        """Get next User-Agent in rotation."""
        with self._lock:
            ua = self.USER_AGENTS[self.index]
            self.index = (self.index + 1) % len(self.USER_AGENTS)
            return ua

    def get_random(self) -> str:
        """Get a random User-Agent."""
        import random
        return random.choice(self.USER_AGENTS)
