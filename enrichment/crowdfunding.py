#!/usr/bin/env python3
"""
Crowdfunding platforms scraping for email discovery.

Scrapes Patreon, Ko-fi, Buy Me a Coffee, and other crowdfunding platforms.
"""

import re
from typing import List
import requests
from bs4 import BeautifulSoup

# Import logging
try:
    from utils.logging_config import get_logger
    logger = get_logger('enrichment.crowdfunding')
except ImportError:
    import logging
    logger = logging.getLogger('enrichment.crowdfunding')


def extract_crowdfunding_urls(text: str) -> List[tuple]:
    """
    Extract crowdfunding platform URLs from text.

    Args:
        text: Text to search

    Returns:
        List of (platform, username) tuples
    """
    patterns = {
        'patreon': r'patreon\.com/([a-zA-Z0-9_-]+)',
        'kofi': r'ko-fi\.com/([a-zA-Z0-9_-]+)',
        'buymeacoffee': r'buymeacoffee\.com/([a-zA-Z0-9_-]+)',
        'gofundme': r'gofundme\.com/f/([a-zA-Z0-9_-]+)',
    }

    results = []
    for platform, pattern in patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.lower() not in ['join', 'create', 'login', 'signup']:
                results.append((platform, match))

    return list(set(results))


def scrape_patreon_email(
    username: str,
    session: requests.Session,
    rate_limiter=None,
    timeout: int = 10
) -> List[str]:
    """
    Scrape email from Patreon page.

    Args:
        username: Patreon username
        session: requests session
        rate_limiter: Optional rate limiter
        timeout: Request timeout

    Returns:
        List of found emails
    """
    if rate_limiter:
        rate_limiter.wait('patreon.com')

    url = f"https://www.patreon.com/{username}"

    try:
        logger.debug(f"Fetching Patreon: {username}")

        response = session.get(url, timeout=timeout)

        if response.status_code == 429:
            logger.warning(f"Rate limited by Patreon for {username}")
            if rate_limiter:
                rate_limiter.report_rate_limit('patreon.com', 120)
            return []

        if response.status_code != 200:
            return []

        # Extract emails from page
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.text)

        # Parse HTML for more structured extraction
        soup = BeautifulSoup(response.text, 'html.parser')

        # Look for mailto links
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            email_match = re.search(r'mailto:([^?&]+)', href, re.I)
            if email_match:
                emails.append(email_match.group(1))

        emails = list(set(emails))

        if emails:
            logger.info(f"✓ Patreon {username}: {emails}")
        else:
            logger.debug(f"⊘ Patreon {username}: no email")

        return emails

    except requests.Timeout:
        logger.warning(f"⏱ Patreon {username}: timeout")
        return []
    except Exception as e:
        logger.error(f"✗ Patreon {username}: {e}")
        return []


def scrape_kofi_email(
    username: str,
    session: requests.Session,
    rate_limiter=None,
    timeout: int = 10
) -> List[str]:
    """
    Scrape email from Ko-fi page.

    Args:
        username: Ko-fi username
        session: requests session
        rate_limiter: Optional rate limiter
        timeout: Request timeout

    Returns:
        List of found emails
    """
    if rate_limiter:
        rate_limiter.wait('ko-fi.com')

    url = f"https://ko-fi.com/{username}"

    try:
        logger.debug(f"Fetching Ko-fi: {username}")

        response = session.get(url, timeout=timeout)

        if response.status_code == 429:
            logger.warning(f"Rate limited by Ko-fi for {username}")
            if rate_limiter:
                rate_limiter.report_rate_limit('ko-fi.com', 120)
            return []

        if response.status_code != 200:
            return []

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.text)

        soup = BeautifulSoup(response.text, 'html.parser')
        mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
        for link in mailto_links:
            href = link.get('href', '')
            email_match = re.search(r'mailto:([^?&]+)', href, re.I)
            if email_match:
                emails.append(email_match.group(1))

        emails = list(set(emails))

        if emails:
            logger.info(f"✓ Ko-fi {username}: {emails}")
        else:
            logger.debug(f"⊘ Ko-fi {username}: no email")

        return emails

    except Exception as e:
        logger.error(f"✗ Ko-fi {username}: {e}")
        return []


def scrape_buymeacoffee_email(
    username: str,
    session: requests.Session,
    rate_limiter=None,
    timeout: int = 10
) -> List[str]:
    """
    Scrape email from Buy Me a Coffee page.

    Args:
        username: Buy Me a Coffee username
        session: requests session
        rate_limiter: Optional rate limiter
        timeout: Request timeout

    Returns:
        List of found emails
    """
    if rate_limiter:
        rate_limiter.wait('buymeacoffee.com')

    url = f"https://www.buymeacoffee.com/{username}"

    try:
        logger.debug(f"Fetching Buy Me a Coffee: {username}")

        response = session.get(url, timeout=timeout)

        if response.status_code == 429:
            logger.warning(f"Rate limited by Buy Me a Coffee for {username}")
            if rate_limiter:
                rate_limiter.report_rate_limit('buymeacoffee.com', 120)
            return []

        if response.status_code != 200:
            return []

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, response.text)
        emails = list(set(emails))

        if emails:
            logger.info(f"✓ Buy Me a Coffee {username}: {emails}")
        else:
            logger.debug(f"⊘ Buy Me a Coffee {username}: no email")

        return emails

    except Exception as e:
        logger.error(f"✗ Buy Me a Coffee {username}: {e}")
        return []


def scrape_crowdfunding_emails(
    text: str,
    session: requests.Session,
    rate_limiter=None
) -> List[str]:
    """
    Extract crowdfunding URLs from text and scrape emails.

    Args:
        text: Text containing potential crowdfunding links
        session: requests session
        rate_limiter: Optional rate limiter

    Returns:
        List of found emails
    """
    platforms_found = extract_crowdfunding_urls(text)

    if not platforms_found:
        logger.debug("No crowdfunding platforms found in text")
        return []

    logger.debug(f"Found crowdfunding platforms: {platforms_found}")

    all_emails = []

    for platform, username in platforms_found:
        if platform == 'patreon':
            emails = scrape_patreon_email(username, session, rate_limiter)
        elif platform == 'kofi':
            emails = scrape_kofi_email(username, session, rate_limiter)
        elif platform == 'buymeacoffee':
            emails = scrape_buymeacoffee_email(username, session, rate_limiter)
        else:
            continue

        all_emails.extend(emails)

    return list(set(all_emails))


# Testing
if __name__ == "__main__":
    print("Crowdfunding platforms scraper module loaded")

    # Test URL extraction
    test_text = """
    Support me on Patreon: https://www.patreon.com/TechReviewer
    Or buy me a coffee: ko-fi.com/techreviewer
    Also at buymeacoffee.com/techreviewer
    """

    platforms = extract_crowdfunding_urls(test_text)
    print(f"Extracted crowdfunding platforms: {platforms}")

    # Test email extraction
    test_html = "Contact: business@example.com for collaborations"
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, test_html)
    print(f"Extracted emails: {emails}")

    print("\n✅ Crowdfunding scraper ready")
    print("Supported platforms: Patreon, Ko-fi, Buy Me a Coffee")
