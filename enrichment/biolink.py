#!/usr/bin/env python3
"""
Link-in-bio page scraping for email extraction.

Creators often use link aggregator services (Linktree, Beacons, etc.) to
centralize all their links. These pages frequently contain contact emails
that aren't published on YouTube directly.
"""

import re
from typing import List, Dict, Optional, Tuple
import requests


# Known link-in-bio platforms and their URL patterns
BIOLINK_PATTERNS = {
    "linktree": r"linktr\.ee/([a-zA-Z0-9._-]+)",
    "beacons": r"beacons\.ai/([a-zA-Z0-9._-]+)",
    "biolink": r"bio\.link/([a-zA-Z0-9._-]+)",
    "komi": r"komi\.io/([a-zA-Z0-9._-]+)",
    "stan": r"stan\.store/([a-zA-Z0-9._-]+)",
    "carrd": r"([a-zA-Z0-9._-]+)\.carrd\.co",
    "taplink": r"taplink\.cc/([a-zA-Z0-9._-]+)",
    "campsite": r"campsite\.bio/([a-zA-Z0-9._-]+)",
    "linkin": r"linkin\.bio/([a-zA-Z0-9._-]+)",
    "lnk": r"lnk\.bio/([a-zA-Z0-9._-]+)",
    "hoo": r"hoo\.be/([a-zA-Z0-9._-]+)",
    "linkpop": r"linkpop\.com/([a-zA-Z0-9._-]+)",
}


def extract_biolink_urls(text: str) -> Dict[str, List[str]]:
    """
    Extract link-in-bio URLs from text.

    Args:
        text: Text to search (YouTube description, external links, etc.)

    Returns:
        Dict mapping platform name to list of full URLs
    """
    if not text:
        return {}

    found_urls: Dict[str, List[str]] = {}

    for platform, pattern in BIOLINK_PATTERNS.items():
        for match in re.finditer(pattern, text, re.IGNORECASE):
            username = match.group(1)

            # Construct full URL
            if platform == "carrd":
                url = f"https://{username}.carrd.co"
            elif platform == "linktree":
                url = f"https://linktr.ee/{username}"
            elif platform == "beacons":
                url = f"https://beacons.ai/{username}"
            elif platform == "biolink":
                url = f"https://bio.link/{username}"
            elif platform == "komi":
                url = f"https://komi.io/{username}"
            elif platform == "stan":
                url = f"https://stan.store/{username}"
            elif platform == "taplink":
                url = f"https://taplink.cc/{username}"
            elif platform == "campsite":
                url = f"https://campsite.bio/{username}"
            elif platform == "linkin":
                url = f"https://linkin.bio/{username}"
            elif platform == "lnk":
                url = f"https://lnk.bio/{username}"
            elif platform == "hoo":
                url = f"https://hoo.be/{username}"
            elif platform == "linkpop":
                url = f"https://linkpop.com/{username}"
            else:
                continue

            if platform not in found_urls:
                found_urls[platform] = []
            if url not in found_urls[platform]:
                found_urls[platform].append(url)

    return found_urls


def scrape_linktree(url: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Scrape emails from Linktree page.

    Args:
        url: Linktree URL
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            return emails

        html = response.text

        # Linktree embeds data in script tags as JSON
        # Look for email in various fields

        # Pattern 1: Direct email links (mailto:)
        mailto_pattern = r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})'
        for match in re.finditer(mailto_pattern, html, re.IGNORECASE):
            email = match.group(1).lower().strip()
            if email not in emails:
                emails.append(email)

        # Pattern 2: JSON embedded email fields
        json_email_pattern = r'"email":\s*"([^"]+@[^"]+)"'
        for match in re.finditer(json_email_pattern, html):
            email = match.group(1).lower().strip()
            if email and "@" in email and email not in emails:
                emails.append(email)

        # Pattern 3: Contact button text/links
        contact_pattern = r'(?:contact|email).*?([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})'
        for match in re.finditer(contact_pattern, html, re.IGNORECASE):
            email = match.group(1).lower().strip()
            if email not in emails:
                emails.append(email)

        # Pattern 4: Use enhanced email extraction on the whole page
        from utils.obfuscation import extract_emails_enhanced
        page_emails = extract_emails_enhanced(html)
        for email in page_emails:
            if email not in emails:
                emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_beacons(url: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Scrape emails from Beacons.ai page.

    Args:
        url: Beacons URL
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            return emails

        html = response.text

        # Beacons structure similar to Linktree
        mailto_pattern = r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})'
        for match in re.finditer(mailto_pattern, html, re.IGNORECASE):
            email = match.group(1).lower().strip()
            if email not in emails:
                emails.append(email)

        # Extract from JSON data
        json_pattern = r'"email":\s*"([^"]+)"'
        for match in re.finditer(json_pattern, html):
            email_candidate = match.group(1)
            if "@" in email_candidate:
                email = email_candidate.lower().strip()
                if email not in emails:
                    emails.append(email)

        # Enhanced extraction
        from utils.obfuscation import extract_emails_enhanced
        page_emails = extract_emails_enhanced(html)
        for email in page_emails:
            if email not in emails:
                emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_generic_biolink(url: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Generic bio link page scraper for any platform.

    Uses multiple strategies to find emails on any link-in-bio page.

    Args:
        url: Bio link URL
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            return emails

        html = response.text

        # Strategy 1: mailto: links
        mailto_pattern = r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})'
        for match in re.finditer(mailto_pattern, html, re.IGNORECASE):
            email = match.group(1).lower().strip()
            if email not in emails:
                emails.append(email)

        # Strategy 2: href with email
        href_email_pattern = r'href=["\']([^"\']*@[^"\']+)["\']'
        for match in re.finditer(href_email_pattern, html):
            potential = match.group(1)
            # Clean up
            potential = potential.replace("mailto:", "").strip()
            if "@" in potential and "." in potential:
                email = potential.lower()
                if email not in emails:
                    emails.append(email)

        # Strategy 3: Meta tags
        meta_pattern = r'<meta[^>]+content=["\']([^"\']*@[^"\']+)["\']'
        for match in re.finditer(meta_pattern, html):
            potential = match.group(1)
            from utils.obfuscation import extract_emails_enhanced
            meta_emails = extract_emails_enhanced(potential)
            for email in meta_emails:
                if email not in emails:
                    emails.append(email)

        # Strategy 4: JSON-LD structured data
        jsonld_pattern = r'<script type="application/ld\+json">([^<]+)</script>'
        for match in re.finditer(jsonld_pattern, html):
            try:
                import json
                data = json.loads(match.group(1))
                # Recursively look for email fields
                def find_emails_in_json(obj):
                    found = []
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            if key.lower() == "email" and isinstance(value, str) and "@" in value:
                                found.append(value.lower())
                            else:
                                found.extend(find_emails_in_json(value))
                    elif isinstance(obj, list):
                        for item in obj:
                            found.extend(find_emails_in_json(item))
                    return found

                json_emails = find_emails_in_json(data)
                for email in json_emails:
                    if email not in emails:
                        emails.append(email)
            except:
                pass

        # Strategy 5: Enhanced extraction on full page
        from utils.obfuscation import extract_emails_enhanced
        page_emails = extract_emails_enhanced(html)
        for email in page_emails:
            if email not in emails:
                emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_biolink_emails(
    text: str,
    session: requests.Session,
    timeout: int = 10
) -> Tuple[List[str], str]:
    """
    Find and scrape all link-in-bio pages from text.

    Args:
        text: Text containing potential biolink URLs
        session: requests.Session to use
        timeout: Request timeout per URL

    Returns:
        Tuple of (emails found, source description)
    """
    biolink_urls = extract_biolink_urls(text)

    if not biolink_urls:
        return [], ""

    all_emails: List[str] = []
    sources: List[str] = []

    # Platform-specific scrapers
    scrapers = {
        "linktree": scrape_linktree,
        "beacons": scrape_beacons,
    }

    for platform, urls in biolink_urls.items():
        for url in urls:
            # Use platform-specific scraper if available, else generic
            scraper = scrapers.get(platform, scrape_generic_biolink)

            try:
                emails = scraper(url, session, timeout)
                if emails:
                    for email in emails:
                        if email not in all_emails:
                            all_emails.append(email)
                    sources.append(f"{platform}:{url}")
            except Exception:
                continue

    source_str = ", ".join(sources) if sources else ""
    return all_emails, source_str


# Testing
if __name__ == "__main__":
    test_texts = [
        "Check out my links: https://linktr.ee/creator",
        "All links: beacons.ai/myprofile",
        "Visit: bio.link/myhandle or creator.carrd.co",
        "My site: stan.store/shop and komi.io/mypage",
    ]

    print("Testing biolink URL extraction:")
    for text in test_texts:
        urls = extract_biolink_urls(text)
        print(f"\nText: {text}")
        print(f"Found: {urls}")
