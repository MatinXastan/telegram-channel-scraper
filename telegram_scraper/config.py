"""
Configuration and constants for the Telegram Scraper.
"""

from typing import Optional, Dict
from pydantic import BaseModel, Field


TELEGRAM_BASE_URL = "https://t.me/s"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Not/A)Brand";v="8", "Chromium";v="126", "Google Chrome";v="126"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

AJAX_HEADERS = {
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


class ScraperConfig(BaseModel):
    """Configuration settings for scraper execution."""
    channel: str = Field(..., description="Channel username or link")
    limit: int = Field(default=20, ge=1, le=1000, description="Max number of posts to scrape")
    proxy: Optional[str] = Field(default=None, description="Proxy URL (e.g., http://127.0.0.1:10809 or socks5://127.0.0.1:10808)")
    timeout: float = Field(default=20.0, description="Network request timeout in seconds")
    headless: bool = Field(default=True, description="Whether to run browser in headless mode")
    download_media: bool = Field(default=False, description="Whether to download photos and media thumbnails")
    output_formats: list[str] = Field(default_factory=lambda: ["json", "excel"], description="Export formats")
    output_dir: str = Field(default="downloads", description="Output directory for files and exports")
    delay_between_requests: float = Field(default=1.0, description="Polite delay in seconds between pagination requests")
