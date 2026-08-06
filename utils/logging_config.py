#!/usr/bin/env python3
"""
Logging configuration for YouTube Email Scraper.

Provides structured logging with different levels for CLI and file output.
"""

import logging
import sys
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(verbose: bool = False, log_file: str = None) -> logging.Logger:
    """
    Setup logging configuration.

    Args:
        verbose: Enable debug logging
        log_file: Optional log file path

    Returns:
        Configured logger
    """
    logger = logging.getLogger('youtube_email_scraper')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler (only warnings and errors by default)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.WARNING if not verbose else logging.DEBUG)

    console_format = '%(levelname)s: %(message)s'
    if verbose:
        console_format = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    console_formatter = ColoredFormatter(console_format, datefmt='%H:%M:%S')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler (all levels)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        file_format = '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if name:
        return logging.getLogger(f'youtube_email_scraper.{name}')
    return logging.getLogger('youtube_email_scraper')
