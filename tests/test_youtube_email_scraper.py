import unittest
from unittest.mock import patch

from youtube_email_scraper import (
    extract_emails,
    has_business_email_gate,
    scrape_channel,
)


EMPTY_META = {
    "description": "",
    "name": "Example Channel",
    "country": "",
    "channel_id": "UC123",
    "subscribers": "10 subscribers",
    "links": [],
}


class BusinessEmailGateTests(unittest.TestCase):
    def test_detects_nested_sign_in_gate(self):
        data = {
            "aboutChannelViewModel": {
                "signInForBusinessEmail": {
                    "content": "Sign in to see email address"
                }
            }
        }
        self.assertTrue(has_business_email_gate(data, ""))

    def test_generic_recaptcha_config_is_not_a_gate(self):
        page_html = 'window.ytcfg={"RECAPTCHA_V3_SITEKEY":"site-key"}'
        self.assertFalse(has_business_email_gate({}, page_html))

    def test_gate_html_fallback(self):
        page_html = '<div>{"signInForBusinessEmail":{"content":"Sign in"}}</div>'
        self.assertTrue(has_business_email_gate({}, page_html))


class ScrapeStatusTests(unittest.TestCase):
    def _scrape(self, meta, data=None):
        with (
            patch("youtube_email_scraper.fetch", return_value="<html></html>"),
            patch("youtube_email_scraper.parse_yt_initial_data", return_value=data or {}),
            patch("youtube_email_scraper.extract_channel_meta", return_value=meta),
        ):
            return scrape_channel(object(), "@example")

    def test_public_email_stays_successful_even_when_gate_exists(self):
        meta = dict(EMPTY_META, description="Contact public@acme.dev")
        data = {"signInForBusinessEmail": {"content": "Sign in"}}
        result = self._scrape(meta, data)
        self.assertEqual(result.status, "ok")
        self.assertEqual(result.emails, ["public@acme.dev"])

    def test_gated_email_has_distinct_status(self):
        data = {"signInForBusinessEmail": {"content": "Sign in"}}
        result = self._scrape(EMPTY_META, data)
        self.assertEqual(result.status, "verification_required")
        self.assertEqual(result.source, "business_email_gate")

    def test_no_email_without_gate_remains_no_email(self):
        result = self._scrape(EMPTY_META)
        self.assertEqual(result.status, "no_email")

    def test_manual_entry_parser_accepts_multiple_emails(self):
        self.assertEqual(
            extract_emails("one@acme.dev; two (at) acme (dot) org"),
            ["one@acme.dev", "two@acme.org"],
        )


if __name__ == "__main__":
    unittest.main()
