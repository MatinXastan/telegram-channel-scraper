"""
Telegram Channel Web Scraper
A high-performance, modular scraper for public Telegram channels.
"""

__version__ = "1.0.0"
__author__ = "MatinXastan"

from .models import TelegramPost, ChannelInfo, ScrapeResult
from .parser import TelegramParser
from .fast_engine import FastTelegramScraper
from .browser_engine import BrowserTelegramScraper
from .exporter import DataExporter

__all__ = [
    "TelegramPost",
    "ChannelInfo",
    "ScrapeResult",
    "TelegramParser",
    "FastTelegramScraper",
    "BrowserTelegramScraper",
    "DataExporter",
]
