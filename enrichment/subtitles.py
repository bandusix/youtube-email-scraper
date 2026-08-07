#!/usr/bin/env python3
"""
YouTube subtitles mining for email discovery.

Extracts emails from YouTube automatic captions/subtitles.
"""

import re
from typing import List
import requests
import xml.etree.ElementTree as ET

# Import logging
try:
    from utils.logging_config import get_logger
    logger = get_logger('enrichment.subtitles')
except ImportError:
    import logging
    logger = logging.getLogger('enrichment.subtitles')


def extract_video_ids_from_channel(html: str, limit: int = 5) -> List[str]:
    """
    Extract video IDs from channel HTML.

    Args:
        html: Channel HTML content
        limit: Maximum number of video IDs to extract

    Returns:
        List of video IDs
    """
    video_ids = []
    pattern = r'"videoId":"([\w\-]{11})"'
    matches = re.findall(pattern, html)

    seen = set()
    for vid in matches:
        if vid not in seen:
            seen.add(vid)
            video_ids.append(vid)
            if len(video_ids) >= limit:
                break

    return video_ids


def get_subtitle_url(video_id: str, lang: str = 'en') -> str:
    """
    Get subtitle/caption URL for a video.

    Args:
        video_id: YouTube video ID
        lang: Language code (default: en)

    Returns:
        Subtitle URL
    """
    return f"https://www.youtube.com/api/timedtext?v={video_id}&lang={lang}"


def fetch_subtitles(
    video_id: str,
    session: requests.Session,
    rate_limiter=None,
    timeout: int = 10
) -> str:
    """
    Fetch subtitles for a video.

    Args:
        video_id: YouTube video ID
        session: requests session
        rate_limiter: Optional rate limiter
        timeout: Request timeout

    Returns:
        Subtitle text (empty string if not available)
    """
    # Apply rate limiting
    if rate_limiter:
        rate_limiter.wait('youtube.com')

    # Try multiple languages
    languages = ['en', 'en-US', 'en-GB']

    for lang in languages:
        url = get_subtitle_url(video_id, lang)

        try:
            logger.debug(f"Fetching subtitles: {video_id} ({lang})")

            response = session.get(url, timeout=timeout)

            if response.status_code == 429:
                logger.warning(f"Rate limited fetching subtitles for {video_id}")
                if rate_limiter:
                    rate_limiter.report_rate_limit('youtube.com', 60)
                break

            if response.status_code == 200 and response.text:
                return response.text

        except Exception as e:
            logger.debug(f"Failed to fetch subtitles for {video_id} ({lang}): {e}")
            continue

    return ""


def extract_emails_from_subtitles(subtitle_xml: str) -> List[str]:
    """
    Extract email addresses from subtitle XML.

    Args:
        subtitle_xml: Subtitle XML content

    Returns:
        List of email addresses
    """
    emails = []

    try:
        # Parse XML
        root = ET.fromstring(subtitle_xml)

        # Extract all text
        text_parts = []
        for text_elem in root.findall('.//text'):
            if text_elem.text:
                text_parts.append(text_elem.text)

        full_text = ' '.join(text_parts)

        # Extract emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found = re.findall(email_pattern, full_text)
        emails.extend(found)

    except ET.ParseError:
        # Try to extract emails from raw text
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        found = re.findall(email_pattern, subtitle_xml)
        emails.extend(found)

    except Exception as e:
        logger.error(f"Error parsing subtitles: {e}")

    return list(set(emails))


def scrape_subtitle_emails(
    video_ids: List[str],
    session: requests.Session,
    rate_limiter=None
) -> List[str]:
    """
    Scrape emails from multiple videos' subtitles.

    Args:
        video_ids: List of YouTube video IDs
        session: requests session
        rate_limiter: Optional rate limiter

    Returns:
        List of found emails
    """
    all_emails = []

    for video_id in video_ids[:5]:  # Limit to 5 videos
        try:
            subtitle_xml = fetch_subtitles(video_id, session, rate_limiter)

            if subtitle_xml:
                emails = extract_emails_from_subtitles(subtitle_xml)
                if emails:
                    logger.info(f"✓ Subtitles {video_id}: {emails}")
                    all_emails.extend(emails)
            else:
                logger.debug(f"⊘ Subtitles {video_id}: no captions available")

        except Exception as e:
            logger.error(f"✗ Subtitles {video_id}: {e}")
            continue

    return list(set(all_emails))


def scrape_channel_subtitle_emails(
    channel_html: str,
    session: requests.Session,
    rate_limiter=None,
    max_videos: int = 5
) -> List[str]:
    """
    Extract video IDs from channel and scrape subtitle emails.

    Args:
        channel_html: Channel HTML content
        session: requests session
        rate_limiter: Optional rate limiter
        max_videos: Maximum videos to check

    Returns:
        List of found emails
    """
    video_ids = extract_video_ids_from_channel(channel_html, limit=max_videos)

    if not video_ids:
        logger.debug("No video IDs found in channel HTML")
        return []

    logger.debug(f"Found {len(video_ids)} videos to check for subtitles")

    return scrape_subtitle_emails(video_ids, session, rate_limiter)


# Testing
if __name__ == "__main__":
    print("YouTube subtitles scraper module loaded")

    # Test video ID extraction
    test_html = '''
    {"videoId":"dQw4w9WgXcQ"}
    {"videoId":"jNQXAC9IVRw"}
    {"videoId":"dQw4w9WgXcQ"}
    '''

    video_ids = extract_video_ids_from_channel(test_html, limit=5)
    print(f"Extracted video IDs: {video_ids}")

    # Test email extraction from subtitle XML
    test_xml = '''<?xml version="1.0" encoding="utf-8" ?>
    <transcript>
        <text start="0">Hello everyone</text>
        <text start="2">Contact me at hello@example.com</text>
        <text start="5">For business inquiries</text>
    </transcript>
    '''

    emails = extract_emails_from_subtitles(test_xml)
    print(f"Extracted emails from subtitles: {emails}")

    print("\n✅ Subtitles scraper ready")
    print("Note: Actual subtitle fetching requires internet connection")
