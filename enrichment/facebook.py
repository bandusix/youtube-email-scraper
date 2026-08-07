#!/usr/bin/env python3
"""
Facebook public pages scraping for email discovery.

Scrapes public Facebook pages for contact email addresses.
"""

import re
from typing import List
import requests
from bs4 import BeautifulSoup

# Import logging
try:
    from utils.logging_config import get_logger
    logger = get_logger('enrichment.facebook')
except ImportError:
    import logging
    logger = logging.getLogger('enrichment.facebook')


def extract_facebook_page_name(text: str) -> List[str]:
    """
    Extract potential Facebook page names from text.

    Args:
        text: Text to search (channel description, links, etc.)

    Returns:
        List of Facebook page names
    """
    patterns = [
        r'facebook\.com/([a-zA-Z0-9._-]+)',
        r'fb\.com/([a-zA-Z0-9._-]+)',
        r'fb\.me/([a-zA-Z0-9._-]+)',
    ]

    pages = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        pages.extend(matches)

    # Filter out common non-page paths
    exclude = ['share', 'sharer', 'pages', 'groups', 'events', 'watch', 'photo']
    pages = [p for p in pages if p.lower() not in exclude and '?' not in p]

    return list(set(pages))


def scrape_facebook_email(
    page_name: str,
    session: requests.Session,
    rate_limiter=None,
    timeout: int = 10
) -> List[str]:
    """
    Scrape email from Facebook public page.

    Args:
        page_name: Facebook page name or ID
        session: requests session
        rate_limiter: Optional rate limiter
        timeout: Request timeout

    Returns:
        List of found emails
    """
    # Apply rate limiting
    if rate_limiter:
        rate_limiter.wait('facebook.com')
        logger.debug(f"Rate limit check passed for facebook.com")

    # Try about page first
    urls = [
        f"https://www.facebook.com/{page_name}/about",
        f"https://m.facebook.com/{page_name}/about",
        f"https://www.facebook.com/{page_name}",
    ]

    emails = []

    for url in urls:
        try:
            logger.debug(f"Fetching Facebook page: {page_name}")

            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            response = session.get(url, headers=headers, timeout=timeout)

            if response.status_code == 429:
                logger.warning(f"Rate limited by Facebook for {page_name}")
                if rate_limiter:
                    rate_limiter.report_rate_limit('facebook.com', 120)
                break

            if response.status_code != 200:
                continue

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Method 1: Look for email in text
            text = soup.get_text()
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            found = re.findall(email_pattern, text)
            emails.extend(found)

            # Method 2: Look for mailto links
            mailto_links = soup.find_all('a', href=re.compile(r'^mailto:', re.I))
            for link in mailto_links:
                href = link.get('href', '')
                email_match = re.search(r'mailto:([^?&]+)', href, re.I)
                if email_match:
                    emails.append(email_match.group(1))

            # Method 3: Look for email in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                content = tag.get('content', '')
                found = re.findall(email_pattern, content)
                emails.extend(found)

            if emails:
                break  # Found emails, no need to try other URLs

        except requests.Timeout:
            logger.warning(f"⏱ Facebook {page_name}: timeout")
            continue
        except requests.RequestException as e:
            logger.error(f"✗ Facebook {page_name}: {e}")
            continue
        except Exception as e:
            logger.error(f"✗ Facebook {page_name}: unexpected error: {e}")
            continue

    # Deduplicate and filter
    emails = list(set(emails))

    # Filter out common non-business emails
    emails = [e for e in emails if not any(x in e.lower() for x in ['noreply', 'no-reply', 'donotreply'])]

    if emails:
        logger.info(f"✓ Facebook {page_name}: {emails}")
    else:
        logger.debug(f"⊘ Facebook {page_name}: no email")

    return emails


def scrape_facebook_emails_from_text(
    text: str,
    session: requests.Session,
    rate_limiter=None
) -> List[str]:
    """
    Extract Facebook page names from text and scrape emails.

    Args:
        text: Text containing potential Facebook links
        session: requests session
        rate_limiter: Optional rate limiter

    Returns:
        List of found emails
    """
    page_names = extract_facebook_page_name(text)

    if not page_names:
        logger.debug("No Facebook page names found in text")
        return []

    logger.debug(f"Found Facebook pages: {page_names}")

    all_emails = []
    for page_name in page_names[:3]:  # Limit to first 3 pages
        emails = scrape_facebook_email(page_name, session, rate_limiter)
        all_emails.extend(emails)

    return list(set(all_emails))


# Testing
if __name__ == "__main__":
    print("Facebook scraper module loaded")

    # Test page name extraction
    test_text = """
    Follow me on Facebook: https://www.facebook.com/TechReviewer
    Or visit fb.com/TechReviewer for updates
    """

    pages = extract_facebook_page_name(test_text)
    print(f"Extracted Facebook pages: {pages}")

    # Test email extraction from HTML
    test_html = """
    <div>Contact us at: support@example.com</div>
    <a href="mailto:business@test.com">Email us</a>
    """

    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, test_html)
    print(f"Extracted emails: {emails}")

    print("\n✅ Facebook scraper ready")
    print("Note: Actual scraping requires internet connection and valid Facebook pages")
