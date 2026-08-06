"""
Utility modules for YouTube Email Scraper.
"""

from .obfuscation import extract_emails_enhanced
from .proxy_manager import ProxyManager
from .cache import RequestCache

__all__ = [
    "extract_emails_enhanced",
    "ProxyManager",
    "RequestCache",
]
