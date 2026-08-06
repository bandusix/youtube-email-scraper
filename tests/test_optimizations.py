#!/usr/bin/env python3
"""
Tests for v2.1 optimizations.
"""

import unittest
import time
from utils.rate_limit import RateLimiter, UserAgentRotator
from utils.concurrent import ScrapingStats
from utils.email_validator import validate_email_format, get_mx_records


class RateLimiterTests(unittest.TestCase):
    def test_basic_rate_limiting(self):
        limiter = RateLimiter(requests_per_second=10)  # 100ms minimum interval

        domain = "example.com"
        start = time.time()

        limiter.wait(domain)
        limiter.wait(domain)

        elapsed = time.time() - start
        # Should take at least 100ms for second request
        self.assertGreater(elapsed, 0.09)

    def test_per_domain_isolation(self):
        limiter = RateLimiter(requests_per_second=1)

        # Different domains shouldn't block each other
        start = time.time()
        limiter.wait("domain1.com")
        limiter.wait("domain2.com")
        elapsed = time.time() - start

        # Should be fast since they're different domains
        self.assertLess(elapsed, 0.5)

    def test_backoff_on_rate_limit(self):
        limiter = RateLimiter()

        limiter.report_rate_limit("example.com", retry_after=2)

        # Should wait for backoff
        start = time.time()
        limiter.wait("example.com")
        elapsed = time.time() - start

        self.assertGreater(elapsed, 1.9)


class UserAgentRotatorTests(unittest.TestCase):
    def test_rotation(self):
        rotator = UserAgentRotator()

        ua1 = rotator.get_next()
        ua2 = rotator.get_next()

        # Should get different user agents
        self.assertNotEqual(ua1, ua2)

    def test_all_valid(self):
        rotator = UserAgentRotator()

        for _ in range(len(rotator.USER_AGENTS) * 2):
            ua = rotator.get_next()
            # Should contain Mozilla
            self.assertIn("Mozilla", ua)


class ScrapingStatsTests(unittest.TestCase):
    def test_stats_calculation(self):
        stats = ScrapingStats(total=10)
        stats.start_time = time.time()

        # Mock result class
        class MockResult:
            def __init__(self, status, source=None):
                self.status = status
                self.source = source

        stats.record_result(MockResult("ok", "about_description"))
        stats.record_result(MockResult("ok", "enrichment:instagram:user"))
        stats.record_result(MockResult("no_email"))

        self.assertEqual(stats.successful, 2)
        self.assertEqual(stats.no_email, 1)
        self.assertEqual(stats.completed, 3)
        self.assertAlmostEqual(stats.success_rate, 66.67, places=1)

    def test_source_tracking(self):
        stats = ScrapingStats()

        class MockResult:
            def __init__(self, status, source=None):
                self.status = status
                self.source = source

        stats.record_result(MockResult("ok", "enrichment:instagram:user1"))
        stats.record_result(MockResult("ok", "enrichment:instagram:user2"))
        stats.record_result(MockResult("ok", "about_description"))

        self.assertEqual(stats.source_counts["enrichment:instagram:user1"], 1)
        self.assertEqual(stats.source_counts["enrichment:instagram:user2"], 1)
        self.assertEqual(stats.source_counts["about_description"], 1)

    def test_report_formatting(self):
        stats = ScrapingStats(total=5)
        stats.start_time = time.time()

        class MockResult:
            def __init__(self, status, source=None):
                self.status = status
                self.source = source

        stats.record_result(MockResult("ok", "about_description"))
        stats.record_result(MockResult("ok", "enrichment:instagram:user"))
        stats.end_time = time.time()

        report = stats.format_report()

        # Should contain key information
        self.assertIn("Success rate", report)
        self.assertIn("Found emails", report)
        self.assertIn("Email sources", report)


class EmailValidatorTests(unittest.TestCase):
    def test_format_validation(self):
        valid_emails = [
            "test@example.com",
            "user.name@example.co.uk",
            "user+tag@example.com",
        ]

        for email in valid_emails:
            self.assertTrue(validate_email_format(email), f"Should be valid: {email}")

        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user @example.com",
        ]

        for email in invalid_emails:
            self.assertFalse(validate_email_format(email), f"Should be invalid: {email}")

    def test_mx_lookup_real_domain(self):
        # Test with a real domain (gmail.com should have MX records)
        mx_records = get_mx_records("gmail.com", timeout=5)

        # Gmail should have MX records
        self.assertGreater(len(mx_records), 0)
        # Should be hostnames
        for mx in mx_records:
            self.assertIn(".", mx)

    def test_mx_lookup_nonexistent_domain(self):
        # Test with clearly non-existent domain
        mx_records = get_mx_records("this-domain-definitely-does-not-exist-12345.com", timeout=2)

        # Should return empty list
        self.assertEqual(len(mx_records), 0)


if __name__ == "__main__":
    unittest.main()
