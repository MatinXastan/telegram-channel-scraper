"""
Utility and helper functions for Telegram URL parsing, text cleaning, and number parsing.
"""

import re
from typing import Optional


def clean_channel_username(input_str: str) -> str:
    """
    Extract the clean channel username from various URL formats or mentions.
    Examples:
        - https://t.me/s/durov -> durov
        - https://t.me/durov -> durov
        - t.me/durov/123 -> durov
        - @durov -> durov
        - durov -> durov
    """
    if not input_str:
        return ""

    cleaned = input_str.strip()

    # Remove query params & fragments
    if "?" in cleaned:
        cleaned = cleaned.split("?")[0]
    if "#" in cleaned:
        cleaned = cleaned.split("#")[0]

    # Remove trailing slashes
    cleaned = cleaned.rstrip("/")

    # Match Telegram URLs
    tme_pattern = r"(?:https?:\/\/)?(?:www\.)?t\.me\/(?:s\/)?([a-zA-Z0-9_+]+)"
    match = re.search(tme_pattern, cleaned, re.IGNORECASE)
    if match:
        return match.group(1)

    # Remove leading @ if present
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]

    return cleaned


def parse_count_str(val: Optional[str]) -> Optional[int]:
    """
    Parse shorthand count string into an integer.
    Examples:
        '1.2K' -> 1200
        '3.5M' -> 3500000
        '850'  -> 850
        '1 240' -> 1240
    """
    if not val:
        return None

    cleaned = val.strip().replace(" ", "").replace(",", "").upper()

    try:
        if cleaned.endswith("K"):
            num = float(cleaned[:-1])
            return int(num * 1000)
        elif cleaned.endswith("M"):
            num = float(cleaned[:-1])
            return int(num * 1_000_000)
        elif cleaned.endswith("B"):
            num = float(cleaned[:-1])
            return int(num * 1_000_000_000)
        elif cleaned.isdigit():
            return int(cleaned)
    except (ValueError, TypeError):
        pass

    return None


def extract_background_image_url(style_attr: Optional[str]) -> Optional[str]:
    """Extract image URL from CSS background-image style."""
    if not style_attr:
        return None

    match = re.search(r"background-image:\s*url\(['\"]?(.*?)['\"]?\)", style_attr, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def sanitize_filename(filename: str, max_length: int = 100) -> str:
    """Sanitize string to be safe for filenames on Windows and UNIX."""
    cleaned = re.sub(r'[\\/*?"<>|]', "_", filename)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:max_length]
