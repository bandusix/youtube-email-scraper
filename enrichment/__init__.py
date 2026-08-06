"""
Email enrichment modules for YouTube Email Scraper.

This package provides additional email discovery strategies beyond
the basic YouTube About page scraping.
"""

from .social_media import scrape_social_emails
from .biolink import scrape_biolink_emails
from .website import scrape_website_emails
from .community import scrape_community_emails

__all__ = [
    "scrape_social_emails",
    "scrape_biolink_emails",
    "scrape_website_emails",
    "scrape_community_emails",
]
