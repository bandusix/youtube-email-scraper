#!/usr/bin/env python3
"""
Email validation utilities using SMTP verification.

Validates email addresses by checking MX records and SMTP server responses
without actually sending emails.
"""

import re
import socket
import smtplib
from typing import List, Tuple, Optional
from dataclasses import dataclass
import dns.resolver


@dataclass
class EmailValidationResult:
    """Result of email validation."""
    email: str
    valid: bool
    reason: str = ""
    mx_records: List[str] = None
    is_catch_all: Optional[bool] = None

    def __post_init__(self):
        if self.mx_records is None:
            self.mx_records = []


def validate_email_format(email: str) -> bool:
    """
    Basic email format validation.

    Args:
        email: Email address to validate

    Returns:
        True if format is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_mx_records(domain: str, timeout: float = 10) -> List[str]:
    """
    Get MX records for a domain.

    Args:
        domain: Domain name
        timeout: DNS query timeout

    Returns:
        List of MX hostnames, sorted by priority
    """
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout

        mx_records = resolver.resolve(domain, 'MX')
        # Sort by priority (lower is higher priority)
        sorted_mx = sorted(mx_records, key=lambda r: r.preference)
        return [str(r.exchange).rstrip('.') for r in sorted_mx]

    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        return []
    except Exception:
        return []


def verify_email_smtp(
    email: str,
    timeout: float = 10,
    check_catch_all: bool = False
) -> EmailValidationResult:
    """
    Verify email address using SMTP.

    This performs MX lookup and SMTP handshake to verify if the email
    address exists, without sending any actual email.

    Args:
        email: Email address to verify
        timeout: Connection timeout in seconds
        check_catch_all: Whether to check for catch-all domains

    Returns:
        EmailValidationResult with validation details
    """
    if not validate_email_format(email):
        return EmailValidationResult(
            email=email,
            valid=False,
            reason="Invalid email format"
        )

    # Extract domain
    try:
        local, domain = email.rsplit('@', 1)
    except ValueError:
        return EmailValidationResult(
            email=email,
            valid=False,
            reason="Cannot parse email address"
        )

    # Get MX records
    mx_records = get_mx_records(domain, timeout=timeout)
    if not mx_records:
        return EmailValidationResult(
            email=email,
            valid=False,
            reason="No MX records found",
            mx_records=[]
        )

    # Try to connect to MX server
    for mx_host in mx_records[:3]:  # Try first 3 MX servers
        try:
            # Connect to SMTP server
            smtp = smtplib.SMTP(timeout=timeout)
            smtp.connect(mx_host)

            # Send HELO
            smtp.helo('mail.example.com')

            # Send MAIL FROM
            smtp.mail('verify@example.com')

            # Send RCPT TO - this is where we check if email exists
            code, message = smtp.rcpt(email)

            smtp.quit()

            # 250 = OK, 251 = User not local (still deliverable)
            if code in (250, 251):
                is_catch_all = None

                # Check for catch-all if requested
                if check_catch_all:
                    is_catch_all = _check_catch_all(mx_host, domain, timeout)

                return EmailValidationResult(
                    email=email,
                    valid=True,
                    reason="SMTP verification successful",
                    mx_records=mx_records,
                    is_catch_all=is_catch_all
                )
            else:
                # Server rejected the email
                return EmailValidationResult(
                    email=email,
                    valid=False,
                    reason=f"SMTP server rejected: {message.decode()}",
                    mx_records=mx_records
                )

        except (socket.timeout, socket.error, smtplib.SMTPException):
            # Try next MX server
            continue

    # All MX servers failed
    return EmailValidationResult(
        email=email,
        valid=False,
        reason="Cannot connect to any MX server",
        mx_records=mx_records
    )


def _check_catch_all(mx_host: str, domain: str, timeout: float) -> bool:
    """
    Check if domain accepts all emails (catch-all).

    Tests by sending a clearly fake email address.
    """
    try:
        import time as time_module
        fake_email = f"nonexistent-test-{int(time_module.time())}@{domain}"

        smtp = smtplib.SMTP(timeout=timeout)
        smtp.connect(mx_host)
        smtp.helo('mail.example.com')
        smtp.mail('verify@example.com')

        code, _ = smtp.rcpt(fake_email)
        smtp.quit()

        # If fake email is accepted, it's catch-all
        return code in (250, 251)

    except:
        return None  # Cannot determine


def batch_verify_emails(
    emails: List[str],
    timeout: float = 10,
    check_catch_all: bool = False
) -> List[EmailValidationResult]:
    """
    Verify multiple email addresses.

    Groups emails by domain to minimize SMTP connections.

    Args:
        emails: List of email addresses
        timeout: Connection timeout
        check_catch_all: Whether to check for catch-all domains

    Returns:
        List of EmailValidationResult
    """
    from collections import defaultdict

    # Group by domain
    by_domain = defaultdict(list)
    for email in emails:
        try:
            domain = email.rsplit('@', 1)[1]
            by_domain[domain].append(email)
        except (ValueError, IndexError):
            continue

    results = []

    # Verify each domain's emails
    for domain, domain_emails in by_domain.items():
        for email in domain_emails:
            result = verify_email_smtp(email, timeout, check_catch_all)
            results.append(result)

    return results


# Testing
if __name__ == "__main__":
    print("Email validation module")

    # Test cases
    test_emails = [
        "test@gmail.com",
        "invalid@nonexistentdomain123456.com",
        "badformat@",
    ]

    for email in test_emails:
        print(f"\nTesting: {email}")
        result = verify_email_smtp(email, timeout=5)
        print(f"  Valid: {result.valid}")
        print(f"  Reason: {result.reason}")
        if result.mx_records:
            print(f"  MX: {result.mx_records[0]}")
