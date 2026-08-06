#!/usr/bin/env python3
"""
Simple disk-based cache for HTTP requests.

Caches HTTP responses to avoid re-fetching the same URLs repeatedly.
Uses file-based storage with TTL expiration.
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any


class RequestCache:
    """
    Disk-based cache for HTTP request results.

    Stores responses as JSON files in a cache directory, with automatic
    expiration based on TTL (time-to-live).
    """

    def __init__(self, cache_dir: str = ".cache", ttl: int = 3600):
        """
        Initialize request cache.

        Args:
            cache_dir: Directory to store cache files
            ttl: Time-to-live in seconds (default 1 hour)
        """
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_path(self, url: str) -> Path:
        """Get cache file path for URL."""
        key = self._get_cache_key(url)
        return self.cache_dir / f"{key}.json"

    def get(self, url: str) -> Optional[str]:
        """
        Get cached response for URL if available and not expired.

        Args:
            url: URL to look up

        Returns:
            Cached response text, or None if not cached or expired
        """
        cache_path = self._get_cache_path(url)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            cached_time = data.get("timestamp", 0)
            cached_content = data.get("content", "")

            # Check if expired
            if time.time() - cached_time > self.ttl:
                # Expired, delete the cache file
                cache_path.unlink()
                return None

            return cached_content

        except (json.JSONDecodeError, OSError):
            # Corrupted cache file, delete it
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(self, url: str, content: str) -> None:
        """
        Store response in cache.

        Args:
            url: URL being cached
            content: Response content to cache
        """
        cache_path = self._get_cache_path(url)

        data = {
            "url": url,
            "timestamp": time.time(),
            "content": content,
        }

        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            # If write fails, just continue without caching
            pass

    def delete(self, url: str) -> None:
        """Delete cached entry for URL."""
        cache_path = self._get_cache_path(url)
        if cache_path.exists():
            cache_path.unlink()

    def clear(self) -> int:
        """
        Clear all cached entries.

        Returns:
            Number of cache files deleted
        """
        count = 0
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
                count += 1
            except OSError:
                pass
        return count

    def clear_expired(self) -> int:
        """
        Clear only expired cache entries.

        Returns:
            Number of expired cache files deleted
        """
        count = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cached_time = data.get("timestamp", 0)
                if now - cached_time > self.ttl:
                    cache_file.unlink()
                    count += 1

            except (json.JSONDecodeError, OSError):
                # Corrupted file, delete it
                cache_file.unlink()
                count += 1

        return count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dict with cache info (total entries, expired, size, etc.)
        """
        total = 0
        expired = 0
        total_size = 0
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            total += 1
            try:
                total_size += cache_file.stat().st_size

                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                cached_time = data.get("timestamp", 0)
                if now - cached_time > self.ttl:
                    expired += 1

            except (json.JSONDecodeError, OSError):
                expired += 1

        return {
            "total_entries": total,
            "expired_entries": expired,
            "valid_entries": total - expired,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir),
            "ttl_seconds": self.ttl,
        }


# Convenience function for use with requests
def cached_get(
    url: str,
    cache: Optional[RequestCache],
    fetcher_func,
    *args,
    **kwargs
) -> str:
    """
    Get URL with caching support.

    Args:
        url: URL to fetch
        cache: RequestCache instance, or None to disable caching
        fetcher_func: Function to call if not cached, signature: (url, *args, **kwargs) -> str
        *args, **kwargs: Additional arguments passed to fetcher_func

    Returns:
        Response text (from cache or fetched)
    """
    if cache:
        cached = cache.get(url)
        if cached is not None:
            return cached

    # Not cached or caching disabled, fetch it
    content = fetcher_func(url, *args, **kwargs)

    # Store in cache
    if cache and content:
        cache.set(url, content)

    return content


# Testing and example usage
if __name__ == "__main__":
    cache = RequestCache(cache_dir=".test_cache", ttl=10)

    print("Testing cache operations:")

    # Set some test data
    test_url = "https://example.com/test"
    test_content = "<html>Test content</html>"

    print(f"Setting cache for {test_url}")
    cache.set(test_url, test_content)

    # Get it back
    result = cache.get(test_url)
    print(f"Retrieved: {result[:50]}...")

    # Check stats
    stats = cache.get_stats()
    print(f"\nCache stats: {stats}")

    # Test expiration
    print("\nWaiting for expiration (TTL=10s)...")
    time.sleep(11)

    result = cache.get(test_url)
    print(f"After expiration: {result}")

    # Cleanup
    cache.clear()
    print("\nCache cleared")

    # Remove test cache dir
    import shutil
    shutil.rmtree(".test_cache", ignore_errors=True)
