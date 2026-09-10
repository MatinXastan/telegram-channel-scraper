"""
Fast Async HTTP-based Telegram Scraper.
Uses HTTPX and BeautifulSoup to scrape Telegram web previews with minimal overhead.
"""

import asyncio
import logging
from typing import Optional, Callable
import httpx
from bs4 import BeautifulSoup

from .config import ScraperConfig, TELEGRAM_BASE_URL, DEFAULT_HEADERS, AJAX_HEADERS
from .models import ScrapeResult, TelegramPost, ChannelInfo
from .parser import TelegramParser
from .utils import clean_channel_username

logger = logging.getLogger(__name__)


class FastTelegramScraper:
    """Ultra-fast, lightweight HTTP scraper for Telegram public channels."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.channel_username = clean_channel_username(config.channel)
        if not self.channel_username:
            raise ValueError(f"Invalid channel identifier: {config.channel}")

    async def scrape(
        self,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> ScrapeResult:
        """
        Scrape latest posts from the channel up to `config.limit`.
        `progress_callback` can be provided with signature: callback(current_count, total_limit)
        """
        posts_map: dict[int, TelegramPost] = {}
        channel_info: Optional[ChannelInfo] = None
        before_id: Optional[int] = None

        # Build proxy configuration if specified
        mounts = None
        proxy_url = self.config.proxy
        transport = None

        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(
            proxy=proxy_url,
            headers=DEFAULT_HEADERS,
            timeout=self.config.timeout,
            follow_redirects=True,
            limits=limits,
        ) as client:
            # 1. First fetch the main channel page
            main_url = f"{TELEGRAM_BASE_URL}/{self.channel_username}"
            logger.info("Fetching initial page: %s", main_url)

            resp = await client.get(main_url)
            if resp.status_code == 404:
                raise ValueError(f"Channel '@{self.channel_username}' not found on Telegram.")
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            channel_info = TelegramParser.parse_channel_info(soup, self.channel_username)

            # Parse initial posts
            initial_posts = TelegramParser.parse_posts(soup, self.channel_username)
            for p in initial_posts:
                posts_map[p.id] = p

            if progress_callback:
                progress_callback(len(posts_map), self.config.limit)

            before_id = TelegramParser.extract_before_id(soup)

            # 2. Paginate backwards if more posts are needed
            while len(posts_map) < self.config.limit and before_id:
                # Polite delay
                if self.config.delay_between_requests > 0:
                    await asyncio.sleep(self.config.delay_between_requests)

                # Fetch earlier posts via ?before=...
                page_url = f"{TELEGRAM_BASE_URL}/{self.channel_username}?before={before_id}"
                logger.info("Paginating earlier posts: %s", page_url)

                # Telegram returns HTML directly or via AJAX headers
                headers = {**DEFAULT_HEADERS, **AJAX_HEADERS}
                page_resp = await client.get(page_url, headers=headers)
                if page_resp.status_code != 200:
                    logger.warning("Pagination request returned status %d. Stopping.", page_resp.status_code)
                    break

                page_soup = BeautifulSoup(page_resp.text, "html.parser")
                page_posts = TelegramParser.parse_posts(page_soup, self.channel_username)

                if not page_posts:
                    logger.info("No more posts returned in pagination.")
                    break

                new_posts_added = 0
                for p in page_posts:
                    if p.id not in posts_map:
                        posts_map[p.id] = p
                        new_posts_added += 1

                if progress_callback:
                    progress_callback(min(len(posts_map), self.config.limit), self.config.limit)

                if new_posts_added == 0:
                    # Prevent infinite loops if duplicate posts are returned
                    break

                next_before = TelegramParser.extract_before_id(page_soup)
                if not next_before or next_before == before_id:
                    # Alternative fallback: minimum post id found - 1
                    min_id = min(posts_map.keys())
                    if min_id <= 1:
                        break
                    before_id = min_id
                else:
                    before_id = next_before

        # Sort posts by ID descending (latest first)
        sorted_posts = sorted(posts_map.values(), key=lambda p: p.id, reverse=True)

        # Slice to requested limit
        trimmed_posts = sorted_posts[: self.config.limit]

        if not channel_info:
            channel_info = ChannelInfo(username=self.channel_username)

        return ScrapeResult(
            channel=channel_info,
            posts=trimmed_posts,
            total_scraped=len(trimmed_posts),
            engine_used="fast_httpx",
        )
