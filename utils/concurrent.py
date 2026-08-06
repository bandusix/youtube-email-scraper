#!/usr/bin/env python3
"""
Concurrent scraping utilities for YouTube Email Scraper.

Provides thread-pool based concurrent processing with progress tracking.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ScrapingStats:
    """Statistics for a scraping session."""

    total: int = 0
    completed: int = 0
    successful: int = 0
    failed: int = 0
    verification_required: int = 0
    no_email: int = 0

    # Source breakdown
    source_counts: dict = field(default_factory=lambda: defaultdict(int))

    # Timing
    start_time: float = 0
    end_time: float = 0

    def record_result(self, result) -> None:
        """Record a scraping result."""
        self.completed += 1

        if result.status == "ok":
            self.successful += 1
            if result.source:
                self.source_counts[result.source] += 1
        elif result.status == "verification_required":
            self.verification_required += 1
        elif result.status == "no_email":
            self.no_email += 1
        else:
            self.failed += 1

    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        end = self.end_time if self.end_time > 0 else time.time()
        return end - self.start_time

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.completed == 0:
            return 0.0
        return (self.successful / self.completed) * 100

    def format_report(self) -> str:
        """Format statistics as a human-readable report."""
        lines = []
        lines.append("\n" + "="*60)
        lines.append("📊 Scraping Statistics Report")
        lines.append("="*60)

        # Summary
        lines.append(f"\n⏱️  Total time: {self.elapsed:.1f}s")
        lines.append(f"📈 Success rate: {self.success_rate:.1f}%")
        lines.append(f"✅ Found emails: {self.successful}/{self.total}")

        if self.verification_required > 0:
            lines.append(f"🔐 Verification required: {self.verification_required}")
        if self.no_email > 0:
            lines.append(f"❌ No email found: {self.no_email}")
        if self.failed > 0:
            lines.append(f"⚠️  Failed: {self.failed}")

        # Source breakdown
        if self.source_counts:
            lines.append(f"\n📍 Email sources:")
            sorted_sources = sorted(
                self.source_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )
            for source, count in sorted_sources:
                percentage = (count / self.successful) * 100 if self.successful > 0 else 0
                # Clean up source name
                display_source = source.replace("enrichment:", "").replace("_", " ").title()
                if source.startswith("enrichment:"):
                    lines.append(f"   🆕 {display_source}: {count} ({percentage:.1f}%)")
                else:
                    lines.append(f"   📺 {display_source}: {count} ({percentage:.1f}%)")

        lines.append("="*60 + "\n")

        return "\n".join(lines)


class ConcurrentScraper:
    """
    Concurrent scraper with progress tracking and statistics.
    """

    def __init__(
        self,
        scrape_func: Callable,
        max_workers: int = 5,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize concurrent scraper.

        Args:
            scrape_func: Function to scrape a single item, signature: (session, item, **kwargs) -> result
            max_workers: Maximum number of concurrent workers
            progress_callback: Optional callback for progress updates, signature: (completed, total, result)
        """
        self.scrape_func = scrape_func
        self.max_workers = max_workers
        self.progress_callback = progress_callback

        self.stats = ScrapingStats()

    def scrape_all(
        self,
        items: List[Any],
        session_factory: Callable,
        **kwargs
    ) -> List[Any]:
        """
        Scrape all items concurrently.

        Args:
            items: List of items to scrape
            session_factory: Function that returns a new session for each worker
            **kwargs: Additional arguments passed to scrape_func

        Returns:
            List of results in the same order as items
        """
        self.stats = ScrapingStats(total=len(items))
        self.stats.start_time = time.time()

        results = [None] * len(items)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_index = {}
            for idx, item in enumerate(items):
                session = session_factory()
                future = executor.submit(self.scrape_func, session, item, **kwargs)
                future_to_index[future] = idx

            # Collect results as they complete
            for future in as_completed(future_to_index):
                idx = future_to_index[future]

                try:
                    result = future.result()
                    results[idx] = result
                    self.stats.record_result(result)

                    if self.progress_callback:
                        self.progress_callback(self.stats.completed, self.stats.total, result)

                except Exception as e:
                    # Create error result
                    from youtube_email_scraper import ChannelResult
                    result = ChannelResult(
                        input=str(items[idx]),
                        status="error",
                        error=str(e)
                    )
                    results[idx] = result
                    self.stats.record_result(result)

                    if self.progress_callback:
                        self.progress_callback(self.stats.completed, self.stats.total, result)

        self.stats.end_time = time.time()

        return results

    def get_stats(self) -> ScrapingStats:
        """Get current statistics."""
        return self.stats


# Testing
if __name__ == "__main__":
    print("Concurrent scraper module loaded successfully")

    # Test stats
    stats = ScrapingStats(total=10)
    stats.start_time = time.time()

    # Simulate some results
    class DummyResult:
        def __init__(self, status, source=None):
            self.status = status
            self.source = source

    stats.record_result(DummyResult("ok", "about_description"))
    stats.record_result(DummyResult("ok", "enrichment:instagram:user1"))
    stats.record_result(DummyResult("ok", "enrichment:linktree:https://linktr.ee/user2"))
    stats.record_result(DummyResult("no_email"))
    stats.record_result(DummyResult("verification_required"))

    stats.end_time = time.time() + 5.5

    print(stats.format_report())
