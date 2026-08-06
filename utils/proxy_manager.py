#!/usr/bin/env python3
"""
Proxy IP pool manager with rotation and failure handling.

Supports rotating through a list of proxy servers to avoid rate limiting
and distribute load. Automatically marks failed proxies and skips them.
"""

import random
import time
from typing import List, Dict, Optional
import requests


class ProxyManager:
    """
    Manages a pool of proxy servers with rotation and failure tracking.

    Supports two rotation strategies:
    - round_robin: cycle through proxies in order
    - random: pick a random proxy each time
    """

    def __init__(
        self,
        proxy_list: List[str],
        rotation: str = "round_robin",
        max_failures: int = 3,
    ):
        """
        Initialize proxy manager.

        Args:
            proxy_list: List of proxy URLs (e.g., ["http://proxy1:8080", ...])
            rotation: "round_robin" or "random"
            max_failures: How many failures before permanently marking proxy as dead
        """
        self.proxies = [p.strip() for p in proxy_list if p.strip()]
        self.rotation = rotation
        self.max_failures = max_failures

        self.current_index = 0
        self.failure_count: Dict[str, int] = {p: 0 for p in self.proxies}
        self.last_used: Dict[str, float] = {}

    def get_next_proxy(self) -> Optional[str]:
        """
        Get the next available proxy according to rotation strategy.

        Returns:
            Proxy URL string, or None if no proxies available
        """
        if not self.proxies:
            return None

        available = [
            p for p in self.proxies if self.failure_count[p] < self.max_failures
        ]

        if not available:
            # All proxies failed, reset failure counts and try again
            self.failure_count = {p: 0 for p in self.proxies}
            available = self.proxies.copy()

        if self.rotation == "random":
            proxy = random.choice(available)
        else:  # round_robin
            # Find next available proxy from current position
            start_idx = self.current_index
            for _ in range(len(self.proxies)):
                proxy = self.proxies[self.current_index]
                self.current_index = (self.current_index + 1) % len(self.proxies)
                if proxy in available:
                    break
            else:
                # Fallback if somehow didn't find one
                proxy = available[0]

        self.last_used[proxy] = time.time()
        return proxy

    def mark_success(self, proxy: str):
        """Mark a proxy as successful, resetting its failure count."""
        if proxy in self.failure_count:
            self.failure_count[proxy] = 0

    def mark_failure(self, proxy: str):
        """Mark a proxy as failed, incrementing its failure count."""
        if proxy in self.failure_count:
            self.failure_count[proxy] += 1

    def get_proxy_dict(self, proxy_url: str) -> Dict[str, str]:
        """
        Convert proxy URL to requests-compatible proxy dict.

        Args:
            proxy_url: Proxy URL like "http://host:port" or "socks5://host:port"

        Returns:
            Dict like {"http": "...", "https": "..."}
        """
        if not proxy_url:
            return {}

        # If proxy doesn't specify protocol, assume http
        if not proxy_url.startswith(("http://", "https://", "socks4://", "socks5://")):
            proxy_url = f"http://{proxy_url}"

        # Use same proxy for both http and https
        return {"http": proxy_url, "https": proxy_url}

    def get_session(self, headers: Optional[Dict] = None) -> requests.Session:
        """
        Create a requests.Session configured with the next available proxy.

        Args:
            headers: Optional custom headers to set on the session

        Returns:
            Configured requests.Session object
        """
        session = requests.Session()

        proxy = self.get_next_proxy()
        if proxy:
            session.proxies.update(self.get_proxy_dict(proxy))
            # Store proxy URL in session for later failure tracking
            session._proxy_url = proxy  # type: ignore

        if headers:
            session.headers.update(headers)

        return session

    def get_stats(self) -> Dict:
        """Get statistics about proxy pool status."""
        total = len(self.proxies)
        failed = sum(1 for p in self.proxies if self.failure_count[p] >= self.max_failures)
        available = total - failed

        return {
            "total": total,
            "available": available,
            "failed": failed,
            "failure_counts": self.failure_count.copy(),
        }

    @classmethod
    def from_file(cls, filepath: str, **kwargs) -> "ProxyManager":
        """
        Load proxy list from a text file (one proxy per line).

        Args:
            filepath: Path to proxy list file
            **kwargs: Additional arguments passed to ProxyManager constructor

        Returns:
            ProxyManager instance
        """
        with open(filepath, "r", encoding="utf-8") as f:
            proxies = [
                line.split("#", 1)[0].strip()
                for line in f
                if line.strip() and not line.strip().startswith("#")
            ]

        return cls(proxies, **kwargs)


def fetch_with_proxy(
    url: str,
    proxy_manager: Optional[ProxyManager],
    headers: Optional[Dict] = None,
    timeout: int = 25,
    retries: int = 3,
) -> str:
    """
    Fetch URL with automatic proxy rotation and retry on failure.

    Args:
        url: URL to fetch
        proxy_manager: ProxyManager instance, or None to use no proxy
        headers: Optional request headers
        timeout: Request timeout in seconds
        retries: Number of retries on failure

    Returns:
        Response text

    Raises:
        RuntimeError: If all retries failed
    """
    last_err = None

    for attempt in range(retries):
        if proxy_manager:
            session = proxy_manager.get_session(headers)
            current_proxy = getattr(session, "_proxy_url", None)
        else:
            session = requests.Session()
            if headers:
                session.headers.update(headers)
            current_proxy = None

        try:
            response = session.get(url, timeout=timeout)
            if response.status_code == 200:
                if current_proxy and proxy_manager:
                    proxy_manager.mark_success(current_proxy)
                return response.text
            else:
                last_err = f"HTTP {response.status_code}"
        except requests.RequestException as e:
            last_err = str(e)

        # Mark proxy as failed if we were using one
        if current_proxy and proxy_manager:
            proxy_manager.mark_failure(current_proxy)

        if attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Failed after {retries} attempts: {last_err}")


# Example usage and testing
if __name__ == "__main__":
    # Test with dummy proxies
    test_proxies = [
        "http://proxy1.example.com:8080",
        "http://proxy2.example.com:8080",
        "http://proxy3.example.com:8080",
    ]

    pm = ProxyManager(test_proxies, rotation="round_robin")

    print("Testing round-robin rotation:")
    for i in range(5):
        proxy = pm.get_next_proxy()
        print(f"  Request {i+1}: {proxy}")

    print("\nTesting failure handling:")
    pm.mark_failure(test_proxies[0])
    pm.mark_failure(test_proxies[0])
    pm.mark_failure(test_proxies[0])  # Now should be marked dead
    print(f"Stats: {pm.get_stats()}")

    print("\nNext 3 proxies (should skip first one):")
    for i in range(3):
        proxy = pm.get_next_proxy()
        print(f"  Request {i+1}: {proxy}")
