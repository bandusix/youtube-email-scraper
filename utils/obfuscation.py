#!/usr/bin/env python3
"""
Enhanced email obfuscation pattern recognition.

Extends the basic EMAIL_RE patterns to handle more creative obfuscations
that creators use to avoid spam while still publishing contact info.
"""

import re
from typing import List


# Unicode variations of @
UNICODE_AT_SYMBOLS = [
    "@",      # normal
    "＠",      # fullwidth (U+FF20)
    "⊕",      # circled plus
    "⍟",      # circled star operator
    "◉",      # fisheye
    "⊛",      # circled asterisk
]

# Build pattern for all bracket styles around 'at'/'dot'
_BRACKET_PAIRS = [
    (r"\(", r"\)"),
    (r"\[", r"\]"),
    (r"\{", r"\}"),
    (r"<", r">"),
]

# Build all variations of bracketed/spaced at/dot
_AT_PATTERNS = []
_DOT_PATTERNS = []

for open_b, close_b in _BRACKET_PAIRS:
    # (at), [AT], {At}, etc.
    _AT_PATTERNS.append(rf"\s*{open_b}\s*[aA][tT]\s*{close_b}\s*")
    _DOT_PATTERNS.append(rf"\s*{open_b}\s*[dD][oO][tT]\s*{close_b}\s*")

# Add space-delimited: " at ", " AT ", " At "
_AT_PATTERNS.append(r"\s+[aA][tT]\s+")
_DOT_PATTERNS.append(r"\s+[dD][oO][tT]\s+")

# Combine
_AT = "(?:" + "|".join(_AT_PATTERNS) + ")"
_DOT = "(?:" + "|".join(_DOT_PATTERNS) + ")"

# Enhanced obfuscated email regex
OBFUSCATED_ENHANCED_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)" + _AT +
    r"([a-zA-Z0-9.\-]+?)" + _DOT + r"([a-zA-Z]{2,24})",
    re.IGNORECASE,
)

# Pattern for reversed emails: moc.elpmaxe@eman -> name@example.com
REVERSED_EMAIL_RE = re.compile(
    r"([a-z]{2,24})\.([a-zA-Z0-9.\-]+?)@([a-zA-Z0-9._%+\-]+)",
    re.IGNORECASE,
)

# Pattern for "AT" / "DOT" in ALL CAPS without brackets (must be word boundaries)
CAPS_AT_DOT_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*AT\s*([a-zA-Z0-9.\-]+?)\s*DOT\s*([a-zA-Z]{2,24})",
    re.IGNORECASE,
)

# HTML entities: &#64; &#x40; &commat;
HTML_ENTITY_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)(?:&#64;|&#x40;|&commat;)([a-zA-Z0-9.\-]+?)\.([a-zA-Z]{2,24})",
    re.IGNORECASE,
)

# Verbose patterns like "name [at symbol] domain [dot] com"
VERBOSE_RE = re.compile(
    r"([a-zA-Z0-9._%+\-]+)\s*"
    r"(?:\[?\s*at\s+symbol\s*\]?|\[?\s*@\s*symbol\s*\]?)\s*"
    r"([a-zA-Z0-9.\-]+?)\s*"
    r"(?:\[?\s*dot\s*\]?|\[?\s*period\s*\]?)\s*"
    r"([a-zA-Z]{2,24})",
    re.IGNORECASE,
)

# Unicode at symbols pattern
UNICODE_AT_RE = re.compile(
    rf"([a-zA-Z0-9._%+\-]+)\s*[{''.join(re.escape(s) for s in UNICODE_AT_SYMBOLS)}]\s*([a-zA-Z0-9.\-]+?)\.([a-zA-Z]{{2,24}})"
)


def decode_html_entities(text: str) -> str:
    """Decode common HTML entities that might hide email parts."""
    import html
    decoded = html.unescape(text)
    # Also handle numeric entities manually in case html.unescape missed some
    decoded = re.sub(r"&#64;", "@", decoded)
    decoded = re.sub(r"&#x40;", "@", decoded, flags=re.IGNORECASE)
    decoded = re.sub(r"&commat;", "@", decoded, flags=re.IGNORECASE)
    return decoded


def extract_emails_enhanced(text: str, existing_extractor=None) -> List[str]:
    """
    Enhanced email extraction with support for creative obfuscations.

    Args:
        text: The text to search for emails
        existing_extractor: Optional existing extract_emails function to call first

    Returns:
        List of found email addresses (deduplicated, lowercase)
    """
    if not text:
        return []

    found = []

    # First, try the existing extractor if provided (handles basic + simple obfuscation)
    if existing_extractor:
        found.extend(existing_extractor(text))

    # Decode HTML entities
    text = decode_html_entities(text)

    # Also try basic email regex on decoded text
    basic_email_re = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,24}')
    for match in basic_email_re.finditer(text):
        email = match.group(0).lower().strip()
        if email not in found:
            found.append(email)

    # Enhanced obfuscated patterns
    for local, dom, tld in OBFUSCATED_ENHANCED_RE.findall(text):
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found:
            found.append(email)

    # CAPS AT/DOT pattern
    for local, dom, tld in CAPS_AT_DOT_RE.findall(text):
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found:
            found.append(email)

    # HTML entity pattern
    for local, dom, tld in HTML_ENTITY_RE.findall(text):
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found:
            found.append(email)

    # Verbose pattern: [at symbol], [period], etc.
    for local, dom, tld in VERBOSE_RE.findall(text):
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found:
            found.append(email)

    # Unicode @ symbols
    for match in UNICODE_AT_RE.finditer(text):
        local, dom, tld = match.groups()
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found:
            found.append(email)

    # Reversed emails: com.example@name -> name@example.com
    for tld, dom, local in REVERSED_EMAIL_RE.findall(text):
        # Reconstruct in correct order
        email = f"{local}@{dom}.{tld}".lower().strip()
        if email not in found and _looks_like_reversed_email(text, tld, dom, local):
            found.append(email)

    return found


def _looks_like_reversed_email(text: str, tld: str, dom: str, local: str) -> bool:
    """
    Heuristic to check if this really looks like a reversed email.
    Avoids false positives like "es.ualizadas@nombre".
    """
    # Check if tld is a common TLD
    common_tlds = {"com", "org", "net", "edu", "gov", "io", "co", "ai", "dev", "me"}
    if tld.lower() not in common_tlds:
        return False

    # Look for context clues: "reversed", "backwards", etc.
    context_window = text[max(0, text.find(f"{tld}.{dom}@{local}") - 50):
                          text.find(f"{tld}.{dom}@{local}") + 100]
    context_hints = ["revers", "backward", "flip", "inverted", "🔄", "↩"]
    if any(hint in context_window.lower() for hint in context_hints):
        return True

    return False


# Test patterns
if __name__ == "__main__":
    test_cases = [
        "Contact: name (at) example (dot) com",
        "Email: name[AT]example[DOT]org",
        "Reach me: name {at} example {dot} net",
        "Contact name AT example DOT com for business",
        "Email: name&#64;example.com",
        "Write to name&commat;example.com",
        "Contact: name [at symbol] example [period] com",
        "Email: name＠example.com",  # fullwidth
        "Reversed: moc.elpmaxe@eman (backwards)",
        "name<at>example<dot>io",
    ]

    for test in test_cases:
        emails = extract_emails_enhanced(test)
        print(f"Input: {test}")
        print(f"Found: {emails}")
        print()
