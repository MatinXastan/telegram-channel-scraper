"""
Browser-based Telegram Scraper powered by Playwright.
Simulates real human interaction in Chromium, supports visual (headed) mode,
auto-scrolling, and clicking pagination buttons.
"""

import asyncio
import logging
from typing import Optional, Callable
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page

from .config import ScraperConfig, TELEGRAM_BASE_URL, DEFAULT_HEADERS
from .models import ScrapeResult, TelegramPost, ChannelInfo
from .parser import TelegramParser
from .utils import clean_channel_username

logger = logging.getLogger(__name__)


class BrowserTelegramScraper:
    """Full browser automation scraper for Telegram channels using Playwright."""

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
        Scrape latest posts using a real Chromium browser instance.
        """
        posts_map: dict[int, TelegramPost] = {}
        channel_info: Optional[ChannelInfo] = None

        launch_kwargs = {
            "headless": self.config.headless,
        }

        if self.config.proxy:
            launch_kwargs["proxy"] = {"server": self.config.proxy}

        async with async_playwright() as p:
            logger.info(
                "Launching Playwright Chromium (headless=%s)...", self.config.headless
            )
            browser: Browser = await p.chromium.launch(**launch_kwargs)

            context = await browser.new_context(
                user_agent=DEFAULT_HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 900},
                locale="en-US",
            )

            page: Page = await context.new_page()
            page.set_default_timeout(int(self.config.timeout * 1000))

            target_url = f"{TELEGRAM_BASE_URL}/{self.channel_username}"
            logger.info("Navigating to: %s", target_url)

            response = await page.goto(target_url, wait_until="domcontentloaded")
            if response and response.status == 404:
                await browser.close()
                raise ValueError(f"Channel '@{self.channel_username}' was not found on Telegram.")

            # Wait for message feed container to be attached
            try:
                await page.wait_for_selector(".tgme_channel_info, .tgme_widget_message", timeout=10000)
            except Exception:
                logger.warning("Main container selector timed out. Proceeding with current DOM.")

            # Extract initial DOM
            html_content = await page.content()
            soup = BeautifulSoup(html_content, "html.parser")
            channel_info = TelegramParser.parse_channel_info(soup, self.channel_username)

            for post in TelegramParser.parse_posts(soup, self.channel_username):
                posts_map[post.id] = post

            if progress_callback:
                progress_callback(min(len(posts_map), self.config.limit), self.config.limit)

            # Pagination loop: scroll up or click the 'Load more' button if more posts are needed
            max_attempts = 30
            attempts = 0

            while len(posts_map) < self.config.limit and attempts < max_attempts:
                attempts += 1
                prev_count = len(posts_map)

                # Check if 'Load more' anchor is present and visible
                more_button = await page.query_selector("a.tme_messages_more")
                if more_button and await more_button.is_visible():
                    try:
                        await more_button.click()
                        await page.wait_for_timeout(1500)
                    except Exception as e:
                        logger.debug("Failed to click 'Load more': %s", e)
                else:
                    # Scroll to the top of the feed to trigger lazy-loading
                    await page.evaluate("window.scrollTo(0, 0)")
                    await page.wait_for_timeout(1500)

                # Re-parse updated page content
                updated_html = await page.content()
                updated_soup = BeautifulSoup(updated_html, "html.parser")
                for post in TelegramParser.parse_posts(updated_soup, self.channel_username):
                    posts_map[post.id] = post

                current_total = min(len(posts_map), self.config.limit)
                if progress_callback:
                    progress_callback(current_total, self.config.limit)

                if len(posts_map) == prev_count:
                    # Try direct query navigation if before_id can be extracted
                    before_id = TelegramParser.extract_before_id(updated_soup)
                    if before_id:
                        paginated_url = f"{TELEGRAM_BASE_URL}/{self.channel_username}?before={before_id}"
                        logger.info("Navigating browser to: %s", paginated_url)
                        await page.goto(paginated_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(1000)
                        html_jump = await page.content()
                        soup_jump = BeautifulSoup(html_jump, "html.parser")
                        for post in TelegramParser.parse_posts(soup_jump, self.channel_username):
                            posts_map[post.id] = post
                    else:
                        logger.info("No further pagination links discovered.")
                        break

            await browser.close()

        sorted_posts = sorted(posts_map.values(), key=lambda p: p.id, reverse=True)
        trimmed_posts = sorted_posts[: self.config.limit]

        if not channel_info:
            channel_info = ChannelInfo(username=self.channel_username)

        return ScrapeResult(
            channel=channel_info,
            posts=trimmed_posts,
            total_scraped=len(trimmed_posts),
            engine_used="browser_playwright",
        )
