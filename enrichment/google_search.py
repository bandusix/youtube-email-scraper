#!/usr/bin/env python3
"""
Google search integration for email discovery.

Uses Google Custom Search API to find emails mentioned on other websites.
"""

import re
from typing import List
import requests

# Import logging
try:
    from utils.logging_config import get_logger
    logger = get_logger('enrichment.google_search')
except ImportError:
    import logging
    logger = logging.getLogger('enrichment.google_search')


def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    return list(set(emails))


def google_search_emails(
    channel_name: str,
    api_key: str = None,
    cse_id: str = None,
    rate_limiter=None,
    max_results: int = 5
) -> List[str]:
    """
    Search Google for emails related to a YouTube channel.

    Args:
        channel_name: YouTube channel name
        api_key: Google API key (optional, tries env var)
        cse_id: Custom Search Engine ID (optional, tries env var)
        rate_limiter: Optional rate limiter
        max_results: Maximum search results to check

    Returns:
        List of found email addresses
    """
    # Try to get API credentials from environment
    if not api_key or not cse_id:
        import os
        api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        cse_id = cse_id or os.environ.get('GOOGLE_CSE_ID')

    if not api_key or not cse_id:
        logger.debug("Google Search disabled: No API credentials")
        return []

    # Apply rate limiting
    if rate_limiter:
        rate_limiter.wait('googleapis.com')

    # Construct search query
    query = f'"{channel_name}" email contact'

    try:
        logger.debug(f"Google Search: {query}")

        # Call Google Custom Search API
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cse_id,
            'q': query,
            'num': max_results
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 429:
            logger.warning("Google Search rate limited")
            if rate_limiter:
                rate_limiter.report_rate_limit('googleapis.com', 60)
            return []

        response.raise_for_status()
        data = response.json()

        # Extract emails from search results
        emails = []

        # Check snippets
        for item in data.get('items', []):
            snippet = item.get('snippet', '')
            title = item.get('title', '')

            # Extract from snippet and title
            found = extract_emails_from_text(snippet + ' ' + title)
            emails.extend(found)

        emails = list(set(emails))  # Deduplicate

        if emails:
            logger.info(f"✓ Google Search {channel_name}: {emails}")
        else:
            logger.debug(f"⊘ Google Search {channel_name}: no email")

        return emails

    except requests.Timeout:
        logger.warning(f"⏱ Google Search {channel_name}: timeout")
        return []
    except requests.RequestException as e:
        logger.error(f"✗ Google Search {channel_name}: {e}")
        return []
    except Exception as e:
        logger.error(f"✗ Google Search {channel_name}: unexpected error: {e}")
        return []


def search_youtube_site(
    channel_handle: str,
    api_key: str = None,
    cse_id: str = None,
    rate_limiter=None
) -> List[str]:
    """
    Search within youtube.com for email mentions.

    Args:
        channel_handle: YouTube channel handle (e.g., @TechReviewer)
        api_key: Google API key
        cse_id: Custom Search Engine ID
        rate_limiter: Optional rate limiter

    Returns:
        List of found email addresses
    """
    if not api_key or not cse_id:
        import os
        api_key = api_key or os.environ.get('GOOGLE_API_KEY')
        cse_id = cse_id or os.environ.get('GOOGLE_CSE_ID')

    if not api_key or not cse_id:
        return []

    # Apply rate limiting
    if rate_limiter:
        rate_limiter.wait('googleapis.com')

    # Search within YouTube site
    query = f'site:youtube.com {channel_handle} @'

    try:
        logger.debug(f"YouTube site search: {query}")

        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cse_id,
            'q': query,
            'num': 3
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 429:
            logger.warning("Google Search rate limited")
            if rate_limiter:
                rate_limiter.report_rate_limit('googleapis.com', 60)
            return []

        response.raise_for_status()
        data = response.json()

        emails = []
        for item in data.get('items', []):
            snippet = item.get('snippet', '')
            found = extract_emails_from_text(snippet)
            emails.extend(found)

        emails = list(set(emails))

        if emails:
            logger.info(f"✓ YouTube site search {channel_handle}: {emails}")

        return emails

    except Exception as e:
        logger.error(f"✗ YouTube site search {channel_handle}: {e}")
        return []


# Testing
if __name__ == "__main__":
    print("Google Search module loaded")

    # Test email extraction
    test_text = "Contact me at hello@example.com or support@test.org for business inquiries"
    emails = extract_emails_from_text(test_text)
    print(f"Extracted: {emails}")

    # Note: Actual search requires API credentials
    print("\nTo use Google Search:")
    print("1. Get API key from: https://console.cloud.google.com/")
    print("2. Create Custom Search Engine: https://programmablesearchengine.google.com/")
    print("3. Set environment variables:")
    print("   export GOOGLE_API_KEY='your-key'")
    print("   export GOOGLE_CSE_ID='your-cse-id'")
