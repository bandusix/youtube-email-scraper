#!/usr/bin/env python3
"""
YouTube community posts and pinned comments scraping.

Creators sometimes share contact information in community posts or
pinned comments that isn't in their channel About page.
"""

import re
import json
from typing import List, Tuple, Optional
import requests


def scrape_community_posts(
    channel_url: str,
    session: requests.Session,
    max_posts: int = 10,
    timeout: int = 15
) -> Tuple[List[str], str]:
    """
    Scrape emails from YouTube community posts.

    Args:
        channel_url: YouTube channel URL
        session: requests.Session to use
        max_posts: Maximum number of posts to check
        timeout: Request timeout

    Returns:
        Tuple of (emails found, source description)
    """
    emails = []

    try:
        # Build community tab URL
        community_url = channel_url.rstrip("/") + "/community"

        response = session.get(community_url, timeout=timeout)
        if response.status_code != 200:
            return emails, ""

        html = response.text

        # Parse ytInitialData
        data = _parse_yt_initial_data(html)
        if not data:
            return emails, ""

        # Extract post content from various possible locations
        post_texts = []

        # Try to find posts in the data structure
        def find_posts(obj, texts_list):
            """Recursively find post content."""
            if isinstance(obj, dict):
                # Look for backstagePostThreadRenderer (community posts)
                if "backstagePostThreadRenderer" in obj:
                    post = obj["backstagePostThreadRenderer"].get("post", {})
                    if "backstagePostRenderer" in post:
                        renderer = post["backstagePostRenderer"]
                        # Extract content text
                        content = renderer.get("contentText", {})
                        if "runs" in content:
                            text = "".join(run.get("text", "") for run in content["runs"])
                            texts_list.append(text)
                        elif "simpleText" in content:
                            texts_list.append(content["simpleText"])

                # Look for postText or contentText fields
                for key in ["postText", "contentText", "description"]:
                    if key in obj:
                        content = obj[key]
                        if isinstance(content, str):
                            texts_list.append(content)
                        elif isinstance(content, dict):
                            if "runs" in content:
                                text = "".join(run.get("text", "") for run in content["runs"])
                                texts_list.append(text)
                            elif "simpleText" in content:
                                texts_list.append(content["simpleText"])

                # Recurse into child objects
                for value in obj.values():
                    find_posts(value, texts_list)

            elif isinstance(obj, list):
                for item in obj:
                    find_posts(item, texts_list)

        find_posts(data, post_texts)

        # Limit to max_posts
        post_texts = post_texts[:max_posts]

        # Extract emails from all post texts
        from utils.obfuscation import extract_emails_enhanced
        for post_text in post_texts:
            post_emails = extract_emails_enhanced(post_text)
            for email in post_emails:
                if email not in emails:
                    emails.append(email)

        if emails:
            return emails, "community_posts"

    except requests.RequestException:
        pass
    except Exception:
        # Catch any parsing errors
        pass

    return emails, ""


def scrape_pinned_comments(
    channel_url: str,
    session: requests.Session,
    max_videos: int = 3,
    timeout: int = 15
) -> Tuple[List[str], str]:
    """
    Scrape emails from pinned comments on popular videos.

    Args:
        channel_url: YouTube channel URL
        session: requests.Session to use
        max_videos: Maximum number of videos to check
        timeout: Request timeout

    Returns:
        Tuple of (emails found, source description)
    """
    emails = []

    try:
        # Get channel's videos page
        videos_url = channel_url.rstrip("/") + "/videos"
        response = session.get(videos_url, timeout=timeout)
        if response.status_code != 200:
            return emails, ""

        html = response.text

        # Extract video IDs from the page
        video_ids = []
        seen = set()
        for vid in re.finditer(r'"videoId":"([\w\-]{11})"', html):
            vid_id = vid.group(1)
            if vid_id not in seen:
                seen.add(vid_id)
                video_ids.append(vid_id)
            if len(video_ids) >= max_videos:
                break

        # Check each video for pinned comments
        for vid_id in video_ids:
            video_url = f"https://www.youtube.com/watch?v={vid_id}"

            try:
                response = session.get(video_url, timeout=timeout)
                if response.status_code != 200:
                    continue

                html = response.text

                # Parse ytInitialData to find pinned comments
                data = _parse_yt_initial_data(html)
                if not data:
                    continue

                # Look for pinned comments
                def find_pinned_comment_text(obj):
                    """Recursively find pinned comment content."""
                    texts = []

                    if isinstance(obj, dict):
                        # Check if this is a pinned comment
                        if "pinnedCommentBadge" in obj or "pinned" in str(obj).lower():
                            # Look for comment text in this subtree
                            if "contentText" in obj:
                                content = obj["contentText"]
                                if isinstance(content, dict) and "runs" in content:
                                    text = "".join(run.get("text", "") for run in content["runs"])
                                    texts.append(text)

                        # Also check commentRenderer
                        if "commentRenderer" in obj:
                            renderer = obj["commentRenderer"]
                            content = renderer.get("contentText", {})
                            if "runs" in content:
                                text = "".join(run.get("text", "") for run in content["runs"])
                                # Check if it's pinned
                                if renderer.get("pinnedCommentBadge") or "pinned" in json.dumps(renderer).lower():
                                    texts.append(text)

                        # Recurse
                        for value in obj.values():
                            texts.extend(find_pinned_comment_text(value))

                    elif isinstance(obj, list):
                        for item in obj:
                            texts.extend(find_pinned_comment_text(item))

                    return texts

                pinned_texts = find_pinned_comment_text(data)

                # Extract emails from pinned comments
                from utils.obfuscation import extract_emails_enhanced
                for text in pinned_texts:
                    comment_emails = extract_emails_enhanced(text)
                    for email in comment_emails:
                        if email not in emails:
                            emails.append(email)

            except requests.RequestException:
                continue
            except Exception:
                continue

        if emails:
            return emails, "pinned_comments"

    except requests.RequestException:
        pass
    except Exception:
        pass

    return emails, ""


def scrape_community_emails(
    channel_url: str,
    session: requests.Session,
    check_posts: bool = True,
    check_comments: bool = True,
    timeout: int = 15
) -> Tuple[List[str], str]:
    """
    Scrape emails from YouTube community features (posts and pinned comments).

    Args:
        channel_url: YouTube channel URL
        session: requests.Session to use
        check_posts: Whether to check community posts
        check_comments: Whether to check pinned comments
        timeout: Request timeout

    Returns:
        Tuple of (emails found, source description)
    """
    all_emails = []
    sources = []

    # Check community posts
    if check_posts:
        emails, source = scrape_community_posts(channel_url, session, timeout=timeout)
        if emails:
            for email in emails:
                if email not in all_emails:
                    all_emails.append(email)
            sources.append(source)

    # Check pinned comments
    if check_comments:
        emails, source = scrape_pinned_comments(channel_url, session, timeout=timeout)
        if emails:
            for email in emails:
                if email not in all_emails:
                    all_emails.append(email)
            sources.append(source)

    source_str = ", ".join(sources) if sources else ""
    return all_emails, source_str


def _parse_yt_initial_data(html: str) -> dict:
    """
    Parse ytInitialData from YouTube page HTML.

    Args:
        html: Page HTML content

    Returns:
        Parsed JSON data as dict, or empty dict if not found
    """
    patterns = [
        r"var ytInitialData\s*=\s*(\{.*?\})\s*;</script>",
        r'window\["ytInitialData"\]\s*=\s*(\{.*?\})\s*;</script>',
        r"ytInitialData\s*=\s*(\{.*?\})\s*;",
    ]

    for pattern in patterns:
        match = re.search(pattern, html, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    return {}


# Testing
if __name__ == "__main__":
    print("Community posts and pinned comments scraper module loaded.")
    print("This module requires a valid YouTube channel URL to test.")
    print("\nExample usage:")
    print("  import requests")
    print("  from enrichment.community import scrape_community_emails")
    print("  session = requests.Session()")
    print("  emails, source = scrape_community_emails('https://youtube.com/@channel', session)")
    print("  print(f'Found: {emails} from {source}')")
