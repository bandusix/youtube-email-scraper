#!/usr/bin/env python3
"""
Tests for v2.4 new enrichment modules.
"""

import unittest
from enrichment.google_search import extract_emails_from_text
from enrichment.facebook import extract_facebook_page_name
from enrichment.subtitles import extract_video_ids_from_channel, extract_emails_from_subtitles
from enrichment.crowdfunding import extract_crowdfunding_urls


class GoogleSearchTests(unittest.TestCase):
    def test_email_extraction(self):
        text = "Contact me at hello@example.com or support@test.org"
        emails = extract_emails_from_text(text)
        self.assertIn('hello@example.com', emails)
        self.assertIn('support@test.org', emails)

    def test_no_emails(self):
        text = "No emails here"
        emails = extract_emails_from_text(text)
        self.assertEqual(len(emails), 0)


class FacebookTests(unittest.TestCase):
    def test_page_name_extraction(self):
        text = "Visit https://www.facebook.com/TechReviewer"
        pages = extract_facebook_page_name(text)
        self.assertIn('TechReviewer', pages)

    def test_fb_short_url(self):
        text = "Check fb.com/MyPage"
        pages = extract_facebook_page_name(text)
        self.assertIn('MyPage', pages)

    def test_exclude_common_paths(self):
        text = "facebook.com/share?url=test"
        pages = extract_facebook_page_name(text)
        self.assertEqual(len(pages), 0)


class SubtitlesTests(unittest.TestCase):
    def test_video_id_extraction(self):
        html = '{"videoId":"dQw4w9WgXcQ"} {"videoId":"jNQXAC9IVRw"}'
        video_ids = extract_video_ids_from_channel(html, limit=5)
        self.assertIn('dQw4w9WgXcQ', video_ids)
        self.assertIn('jNQXAC9IVRw', video_ids)

    def test_duplicate_removal(self):
        html = '{"videoId":"dQw4w9WgXcQ"} {"videoId":"dQw4w9WgXcQ"} {"videoId":"jNQXAC9IVRw"}'
        video_ids = extract_video_ids_from_channel(html, limit=10)
        self.assertEqual(len(video_ids), 2)

    def test_email_from_subtitles(self):
        xml = '''<?xml version="1.0"?>
        <transcript>
            <text>Contact hello@example.com</text>
        </transcript>
        '''
        emails = extract_emails_from_subtitles(xml)
        self.assertIn('hello@example.com', emails)


class CrowdfundingTests(unittest.TestCase):
    def test_patreon_extraction(self):
        text = "Support at patreon.com/creator"
        platforms = extract_crowdfunding_urls(text)
        self.assertIn(('patreon', 'creator'), platforms)

    def test_kofi_extraction(self):
        text = "ko-fi.com/mycreator"
        platforms = extract_crowdfunding_urls(text)
        self.assertIn(('kofi', 'mycreator'), platforms)

    def test_buymeacoffee_extraction(self):
        text = "buymeacoffee.com/user123"
        platforms = extract_crowdfunding_urls(text)
        self.assertIn(('buymeacoffee', 'user123'), platforms)

    def test_multiple_platforms(self):
        text = "patreon.com/a and ko-fi.com/b"
        platforms = extract_crowdfunding_urls(text)
        self.assertEqual(len(platforms), 2)


if __name__ == "__main__":
    unittest.main()
