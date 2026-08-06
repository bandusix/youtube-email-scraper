#!/usr/bin/env python3
"""
Tests for enrichment modules.
"""

import unittest
from utils.obfuscation import extract_emails_enhanced
from enrichment.social_media import extract_social_handles
from enrichment.biolink import extract_biolink_urls


class EnhancedObfuscationTests(unittest.TestCase):
    def test_caps_at_dot(self):
        text = "Contact name AT example DOT com for business"
        emails = extract_emails_enhanced(text)
        self.assertIn("name@example.com", emails)

    def test_html_entities(self):
        text = "Email: name&#64;example.com"
        emails = extract_emails_enhanced(text)
        self.assertIn("name@example.com", emails)

    def test_unicode_at(self):
        text = "Contact: name＠example.com"  # fullwidth @
        emails = extract_emails_enhanced(text)
        self.assertIn("name@example.com", emails)

    def test_verbose_pattern(self):
        text = "Contact: name [at symbol] example [period] com"
        emails = extract_emails_enhanced(text)
        self.assertIn("name@example.com", emails)

    def test_multiple_bracket_styles(self):
        texts = [
            "name (at) example (dot) com",
            "name [at] example [dot] com",
            "name {at} example {dot} com",
            "name <at> example <dot> com",
        ]
        for text in texts:
            emails = extract_emails_enhanced(text)
            self.assertIn("name@example.com", emails, f"Failed for: {text}")


class SocialHandleExtractionTests(unittest.TestCase):
    def test_instagram_extraction(self):
        text = "Follow me on Instagram: @techreviewer"
        handles = extract_social_handles(text)
        self.assertIn("techreviewer", handles["instagram"])

    def test_instagram_url(self):
        text = "https://www.instagram.com/businessaccount/"
        handles = extract_social_handles(text)
        self.assertIn("businessaccount", handles["instagram"])

    def test_twitter_extraction(self):
        text = "Twitter: @techperson"
        handles = extract_social_handles(text)
        self.assertIn("techperson", handles["twitter"])

    def test_tiktok_extraction(self):
        text = "TikTok: @creator"
        handles = extract_social_handles(text)
        self.assertIn("creator", handles["tiktok"])

    def test_multiple_platforms(self):
        text = "IG: @myinsta | Twitter: @mytwitter | TikTok: @mytiktok"
        handles = extract_social_handles(text)
        self.assertIn("myinsta", handles["instagram"])
        self.assertIn("mytwitter", handles["twitter"])
        self.assertIn("mytiktok", handles["tiktok"])


class BiolinkUrlExtractionTests(unittest.TestCase):
    def test_linktree_extraction(self):
        text = "Check out my links: https://linktr.ee/creator"
        urls = extract_biolink_urls(text)
        self.assertIn("linktree", urls)
        self.assertEqual(urls["linktree"][0], "https://linktr.ee/creator")

    def test_beacons_extraction(self):
        text = "All links: beacons.ai/myprofile"
        urls = extract_biolink_urls(text)
        self.assertIn("beacons", urls)
        self.assertEqual(urls["beacons"][0], "https://beacons.ai/myprofile")

    def test_carrd_extraction(self):
        text = "Visit: creator.carrd.co"
        urls = extract_biolink_urls(text)
        self.assertIn("carrd", urls)
        self.assertEqual(urls["carrd"][0], "https://creator.carrd.co")

    def test_multiple_platforms(self):
        text = "linktr.ee/user1 or beacons.ai/user2 or bio.link/user3"
        urls = extract_biolink_urls(text)
        self.assertIn("linktree", urls)
        self.assertIn("beacons", urls)
        self.assertIn("biolink", urls)


if __name__ == "__main__":
    unittest.main()
