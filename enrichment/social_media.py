#!/usr/bin/env python3
"""
Social media cross-reference email extraction.

Extracts social media handles from YouTube descriptions and follows them
to Instagram, Twitter/X, and TikTok to find business emails that creators
publish on those platforms but not on YouTube.
"""

import re
import time
from typing import List, Dict, Optional, Set
import requests


def extract_social_handles(text: str) -> Dict[str, List[str]]:
    """
    Extract social media usernames/handles from text.

    Args:
        text: Text to search (typically channel description or links)

    Returns:
        Dict mapping platform to list of found handles
    """
    if not text:
        return {}

    handles: Dict[str, List[str]] = {
        "instagram": [],
        "twitter": [],
        "tiktok": [],
        "facebook": [],
    }

    # Instagram patterns
    instagram_patterns = [
        r"instagram\.com/([a-zA-Z0-9._]+)",
        r"instagr\.am/([a-zA-Z0-9._]+)",
        r"@([a-zA-Z0-9._]+)\s+(?:on\s+)?instagram",
        r"instagram:\s*@?([a-zA-Z0-9._]+)",
        r"(?:ig|insta):\s*@?([a-zA-Z0-9._]+)",
    ]
    for pattern in instagram_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1).strip()
            if handle and handle not in handles["instagram"]:
                handles["instagram"].append(handle)

    # Twitter/X patterns
    twitter_patterns = [
        r"twitter\.com/([a-zA-Z0-9_]+)",
        r"x\.com/([a-zA-Z0-9_]+)",
        r"@([a-zA-Z0-9_]+)\s*(?:on\s+)?(?:twitter|x\.com)",
        r"(?:twitter|tweet):\s*@?([a-zA-Z0-9_]+)",
    ]
    for pattern in twitter_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1).strip()
            # Filter out common false positives
            if handle and handle.lower() not in ("intent", "share", "status") and handle not in handles["twitter"]:
                handles["twitter"].append(handle)

    # TikTok patterns
    tiktok_patterns = [
        r"tiktok\.com/@([a-zA-Z0-9._]+)",
        r"@([a-zA-Z0-9._]+)\s*(?:on\s+)?tiktok",
        r"tiktok:\s*@?([a-zA-Z0-9._]+)",
    ]
    for pattern in tiktok_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1).strip()
            if handle and handle not in handles["tiktok"]:
                handles["tiktok"].append(handle)

    # Facebook patterns
    facebook_patterns = [
        r"facebook\.com/([a-zA-Z0-9.]+)",
        r"fb\.com/([a-zA-Z0-9.]+)",
        r"fb\.me/([a-zA-Z0-9.]+)",
    ]
    for pattern in facebook_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            handle = match.group(1).strip()
            # Filter out common paths
            if handle and handle.lower() not in ("sharer", "share", "pages", "groups", "events") and handle not in handles["facebook"]:
                handles["facebook"].append(handle)

    return handles


def scrape_instagram_email(username: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Scrape email from Instagram public profile.

    Instagram business/creator accounts often display an email button or
    email in their bio.

    Args:
        username: Instagram username
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        url = f"https://www.instagram.com/{username}/"
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            return emails

        html = response.text

        # Instagram embeds profile data in script tags as JSON
        # Look for business email in various places

        # Pattern 1: business_email field in JSON
        email_pattern = r'"business_email":\s*"([^"]+)"'
        for match in re.finditer(email_pattern, html):
            email = match.group(1).strip()
            if email and "@" in email and email not in emails:
                emails.append(email.lower())

        # Pattern 2: public_email field
        email_pattern2 = r'"public_email":\s*"([^"]+)"'
        for match in re.finditer(email_pattern2, html):
            email = match.group(1).strip()
            if email and "@" in email and email not in emails:
                emails.append(email.lower())

        # Pattern 3: In biography text
        bio_pattern = r'"biography":\s*"([^"]+)"'
        for match in re.finditer(bio_pattern, html):
            bio_text = match.group(1)
            # Decode unicode escapes
            try:
                bio_text = bio_text.encode().decode('unicode_escape')
            except:
                pass
            # Use the enhanced email extractor
            from utils.obfuscation import extract_emails_enhanced
            bio_emails = extract_emails_enhanced(bio_text)
            for email in bio_emails:
                if email not in emails:
                    emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_twitter_email(username: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Scrape email from Twitter/X public profile.

    Note: Twitter's new structure makes this challenging without API access.
    This tries to extract from publicly visible bio/description.

    Args:
        username: Twitter username
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        # Try both twitter.com and x.com
        for domain in ["twitter.com", "x.com"]:
            url = f"https://{domain}/{username}"
            response = session.get(url, timeout=timeout)
            if response.status_code != 200:
                continue

            html = response.text

            # Look for description/bio in meta tags
            desc_pattern = r'<meta\s+(?:name|property)="description"\s+content="([^"]+)"'
            for match in re.finditer(desc_pattern, html):
                desc_text = match.group(1)
                from utils.obfuscation import extract_emails_enhanced
                desc_emails = extract_emails_enhanced(desc_text)
                for email in desc_emails:
                    if email not in emails:
                        emails.append(email)

            # Also check for JSON-LD structured data
            jsonld_pattern = r'<script type="application/ld\+json">([^<]+)</script>'
            for match in re.finditer(jsonld_pattern, html):
                try:
                    import json
                    data = json.loads(match.group(1))
                    # Look for email in various fields
                    if isinstance(data, dict):
                        for key in ["email", "contactPoint"]:
                            if key in data:
                                value = data[key]
                                if isinstance(value, str) and "@" in value:
                                    if value not in emails:
                                        emails.append(value.lower())
                except:
                    pass

            if emails:
                break

    except requests.RequestException:
        pass

    return emails


def scrape_tiktok_email(username: str, session: requests.Session, timeout: int = 10) -> List[str]:
    """
    Scrape email from TikTok public profile.

    TikTok business accounts sometimes show email in bio.

    Args:
        username: TikTok username (without @)
        session: requests.Session to use
        timeout: Request timeout

    Returns:
        List of found email addresses
    """
    emails = []

    try:
        # Ensure username starts with @
        if not username.startswith("@"):
            username = f"@{username}"

        url = f"https://www.tiktok.com/{username}"
        response = session.get(url, timeout=timeout)
        if response.status_code != 200:
            return emails

        html = response.text

        # TikTok embeds data in script tags
        # Look for bio/description
        desc_pattern = r'"desc":\s*"([^"]+)"'
        for match in re.finditer(desc_pattern, html):
            desc_text = match.group(1)
            # Decode unicode escapes
            try:
                desc_text = desc_text.encode().decode('unicode_escape')
            except:
                pass
            from utils.obfuscation import extract_emails_enhanced
            desc_emails = extract_emails_enhanced(desc_text)
            for email in desc_emails:
                if email not in emails:
                    emails.append(email)

        # Also check meta description
        meta_pattern = r'<meta\s+name="description"\s+content="([^"]+)"'
        for match in re.finditer(meta_pattern, html):
            desc_text = match.group(1)
            from utils.obfuscation import extract_emails_enhanced
            meta_emails = extract_emails_enhanced(desc_text)
            for email in meta_emails:
                if email not in emails:
                    emails.append(email)

    except requests.RequestException:
        pass

    return emails


def scrape_social_emails(
    text: str,
    session: requests.Session,
    platforms: Optional[List[str]] = None,
    delay: float = 1.0
) -> tuple[List[str], str]:
    """
    Extract and follow social media links to find emails.

    Args:
        text: Text to search for social media handles (YouTube description, etc.)
        session: requests.Session to use
        platforms: List of platforms to check, or None for all
        delay: Delay between requests in seconds

    Returns:
        Tuple of (emails found, source description)
    """
    if platforms is None:
        platforms = ["instagram", "twitter", "tiktok"]

    handles = extract_social_handles(text)
    all_emails: List[str] = []
    sources: List[str] = []

    scrapers = {
        "instagram": scrape_instagram_email,
        "twitter": scrape_twitter_email,
        "tiktok": scrape_tiktok_email,
    }

    for platform in platforms:
        if platform not in handles or not handles[platform]:
            continue

        scraper = scrapers.get(platform)
        if not scraper:
            continue

        for handle in handles[platform]:
            try:
                emails = scraper(handle, session)
                if emails:
                    for email in emails:
                        if email not in all_emails:
                            all_emails.append(email)
                    sources.append(f"{platform}:{handle}")
                time.sleep(delay)
            except Exception:
                # Continue with next handle on error
                continue

    source_str = ", ".join(sources) if sources else ""
    return all_emails, source_str


# Testing
if __name__ == "__main__":
    test_texts = [
        "Follow me on Instagram: @techreviewer and Twitter @techperson",
        "Contact: https://www.instagram.com/businessaccount/",
        "TikTok: @creator | IG: creator.official",
        "Find me: instagram.com/myhandle, twitter.com/mytwitter",
    ]

    print("Testing social handle extraction:")
    for text in test_texts:
        handles = extract_social_handles(text)
        print(f"\nText: {text}")
        print(f"Found: {handles}")
