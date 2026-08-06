#!/usr/bin/env python3
"""
Website deep crawling for email extraction.

When a creator links to their website, crawl common contact pages
(/contact, /about, /press, etc.) to find business emails.
"""

import re
from typing import List, Set, Tuple, Optional
from urllib.parse import urljoin, urlparse
import requests


# Common paths that often contain contact information
CONTACT_PATHS = [
    "/contact",
    "/contact-us",
    "/contactus",
    "/about",
    "/about-us",
    "/aboutus",
    "/press",
    "/media",
    "/business",
    "/partnerships",
    "/collaborate",
    "/work-with-us",
    "/inquiries",
    "/hello",
]


def normalize_url(url: str) -> str:
    """Ensure URL has protocol."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_links_from_html(html: str, base_url: str) -> List[str]:
    """
    Extract all links from HTML that might lead to contact pages.

    Args:
        html: HTML content
        base_url: Base URL for resolving relative links

    Returns:
        List of absolute URLs
    """
    links = []

    # Find all href attributes
    href_pattern = r'href=["\']([^"\']+)["\']'
    for match in re.finditer(href_pattern, html, re.IGNORECASE):
        href = match.group(1)

        # Skip anchors, javascript, mailto, tel
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        # Make absolute
        absolute_url = urljoin(base_url, href)

        # Only keep links from same domain (avoid external sites)
        if urlparse(absolute_url).netloc == urlparse(base_url).netloc:
            links.append(absolute_url)

    return links


def is_contact_page(url: str, html: str) -> bool:
    """
    Heuristic to determine if a page is likely a contact page.

    Args:
        url: Page URL
        html: Page HTML content

    Returns:
        True if page likely contains contact information
    """
    url_lower = url.lower()

    # Check URL path
    contact_keywords = ["contact", "about", "press", "media", "business", "inquiries"]
    if any(keyword in url_lower for keyword in contact_keywords):
        return True

    # Check page content
    html_lower = html.lower()
    content_keywords = [
        "contact us", "get in touch", "reach out", "email us",
        "business inquiries", "press inquiries", "partnerships",
        "work with us", "collaborate", "send us a message"
    ]
    keyword_count = sum(1 for keyword in content_keywords if keyword in html_lower)

    # If multiple contact keywords found, likely a contact page
    return keyword_count >= 2


def scrape_page_emails(url: str, session: requests.Session, timeout: int = 15) -> List[str]:
    """
    Scrape emails from a single web page.

    Args:
        url: URL to scrape
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        response = session.get(url, timeout=timeout, allow_redirects=True)
        if response.status_code != 200:
            return emails

        html = response.text

        # Use enhanced email extraction
        from utils.obfuscation import extract_emails_enhanced
        page_emails = extract_emails_enhanced(html)

        # Filter out likely false positives (common in scripts/examples)
        exclude_domains = ["example.com", "test.com", "localhost", "127.0.0.1"]
        for email in page_emails:
            domain = email.split("@")[1] if "@" in email else ""
            if domain not in exclude_domains and email not in emails:
                emails.append(email)

        # Also check meta tags specifically
        meta_pattern = r'<meta[^>]+content=["\']([^"\']*@[^"\']+)["\']'
        for match in re.finditer(meta_pattern, html):
            meta_emails = extract_emails_enhanced(match.group(1))
            for email in meta_emails:
                if email not in emails:
                    emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_website_emails(
    website_url: str,
    session: requests.Session,
    max_depth: int = 2,
    max_pages: int = 10,
    timeout: int = 15
) -> Tuple[List[str], str]:
    """
    Deep crawl website to find contact emails.

    Strategy:
    1. Try common contact page paths directly
    2. Scrape homepage and look for contact links
    3. Follow promising links up to max_depth

    Args:
        website_url: Base website URL
        session: requests.Session to use
        max_depth: Maximum link depth to follow
        max_pages: Maximum number of pages to check
        timeout: Request timeout per page

    Returns:
        Tuple of (emails found, source description)
    """
    website_url = normalize_url(website_url)
    if not website_url:
        return [], ""

    all_emails: List[str] = []
    sources: List[str] = []
    visited: Set[str] = set()
    to_visit: List[Tuple[str, int]] = []  # (url, depth)

    # Strategy 1: Try known contact paths directly
    base_domain = urlparse(website_url).netloc
    for path in CONTACT_PATHS:
        contact_url = urljoin(website_url, path)
        if contact_url not in visited:
            to_visit.append((contact_url, 0))

    # Strategy 2: Start from homepage
    to_visit.insert(0, (website_url, 0))

    pages_checked = 0

    while to_visit and pages_checked < max_pages:
        current_url, depth = to_visit.pop(0)

        if current_url in visited:
            continue

        visited.add(current_url)
        pages_checked += 1

        # Scrape this page
        try:
            emails = scrape_page_emails(current_url, session, timeout)
            if emails:
                for email in emails:
                    if email not in all_emails:
                        all_emails.append(email)
                sources.append(current_url)

            # If we found emails or reached max depth, don't crawl deeper from this page
            if emails or depth >= max_depth:
                continue

            # Get the page HTML to extract more links
            response = session.get(current_url, timeout=timeout, allow_redirects=True)
            if response.status_code == 200:
                html = response.text

                # Only follow links from pages that look like they might lead to contact info
                if depth == 0 or is_contact_page(current_url, html):
                    # Extract links
                    links = extract_links_from_html(html, current_url)

                    # Prioritize links that look like contact pages
                    contact_links = []
                    other_links = []

                    for link in links:
                        if link not in visited:
                            link_lower = link.lower()
                            if any(kw in link_lower for kw in ["contact", "about", "press", "media", "business"]):
                                contact_links.append((link, depth + 1))
                            elif depth < max_depth - 1:  # Only add other links if not too deep
                                other_links.append((link, depth + 1))

                    # Add contact links first (higher priority)
                    to_visit.extend(contact_links[:5])  # Limit to top 5 contact links
                    to_visit.extend(other_links[:3])    # Limit to top 3 other links

        except requests.RequestException:
            continue

    # Build source description
    if sources:
        # Show first 2 sources
        source_str = f"website:{base_domain} ({', '.join(sources[:2])}{'...' if len(sources) > 2 else ''})"
    else:
        source_str = ""

    return all_emails, source_str


# Testing
if __name__ == "__main__":
    import sys

    # Test URL extraction
    test_html = '''
    <html>
    <a href="/contact">Contact Us</a>
    <a href="/about">About</a>
    <a href="https://external.com">External</a>
    <a href="#anchor">Anchor</a>
    </html>
    '''

    links = extract_links_from_html(test_html, "https://example.com")
    print(f"Extracted links: {links}")

    # Test contact page detection
    contact_html = "<html><h1>Contact Us</h1><p>Get in touch for business inquiries</p></html>"
    print(f"Is contact page: {is_contact_page('https://example.com/contact', contact_html)}")

    if len(sys.argv) > 1:
        # Live test with actual URL
        import requests
        session = requests.Session()
        test_url = sys.argv[1]
        print(f"\nTesting with: {test_url}")
        emails, source = scrape_website_emails(test_url, session, max_depth=1, max_pages=5)
        print(f"Found emails: {emails}")
        print(f"Source: {source}")
