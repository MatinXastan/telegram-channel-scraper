"""
Main entry point for Telegram Channel Web Scraper.
Supports both interactive wizard and command-line arguments.
"""

import sys
import os

# Fix Windows console encoding for Persian characters and Unicode
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import asyncio
from pathlib import Path
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Prompt, IntPrompt, Confirm

from telegram_scraper.config import ScraperConfig
from telegram_scraper.fast_engine import FastTelegramScraper
from telegram_scraper.browser_engine import BrowserTelegramScraper
from telegram_scraper.exporter import DataExporter
from telegram_scraper.models import ScrapeResult
from telegram_scraper.utils import clean_channel_username

console = Console(file=sys.stdout, highlight=False)


def print_banner():
    """Print an attractive banner in the console."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════╗
    ║          🚀 TELEGRAM CHANNEL PROFESSIONAL WEB SCRAPER          ║
    ║        استخراج پیشرفته و خودکار پست‌ها و رسانه‌های تلگرام         ║
    ╚═══════════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def display_channel_summary(result: ScrapeResult):
    """Display extracted channel profile information in a Rich table."""
    ch = result.channel
    table = Table(title="📌 اطلاعات کانال استخراج‌شده", show_header=True, header_style="bold magenta")
    table.add_column("مشخصه", style="cyan", width=25)
    table.add_column("مقدار", style="green")

    table.add_row("آیدی کانال", f"@{ch.username}")
    table.add_row("عنوان کانال", ch.title or "نامشخص")
    table.add_row("تعداد اعضا / سابسکرایبر", ch.subscribers or "نامشخص")
    table.add_row("تأیید رسمی (Verified)", "✅ بله" if ch.is_verified else "❌ خیر")
    if ch.description:
        desc_preview = ch.description[:100] + ("..." if len(ch.description) > 100 else "")
        table.add_row("توضیحات (Bio)", desc_preview)
    table.add_row("موتور استخراج", result.engine_used)
    table.add_row("تعداد پست‌های استخراج‌شده", str(result.total_scraped))

    console.print(table)


def display_posts_preview(result: ScrapeResult, max_display: int = 5):
    """Display a quick table preview of the latest scraped posts."""
    table = Table(title=f"📋 پیش‌نمایش {min(max_display, len(result.posts))} پست اخیر", header_style="bold blue")
    table.add_column("ID", style="dim", width=8)
    table.add_column("تاریخ", style="cyan", width=18)
    table.add_column("بازدید", style="yellow", width=10)
    table.add_column("واکنش‌ها", style="magenta", width=12)
    table.add_column("رسانه", style="blue", width=10)
    table.add_column("متن خلاصه", style="white")

    for post in result.posts[:max_display]:
        text_preview = (post.text[:60] + "...") if len(post.text) > 60 else (post.text or "[فاقد متن]")
        text_preview = text_preview.replace("\n", " ")
        media_types = ",".join(set(m.type for m in post.media)) or "-"
        reactions_str = f"{post.total_reactions_count} ری‌اکشن" if post.total_reactions_count else "-"
        date_str = (post.date_formatted or post.date_iso or "-")[:16]

        table.add_row(
            str(post.id),
            date_str,
            post.views or "-",
            reactions_str,
            media_types,
            text_preview,
        )

    console.print(table)


async def run_scraper(
    config: ScraperConfig,
    engine_name: str = "browser",
) -> ScrapeResult:
    """Execute the scraping workflow with a live progress bar."""
    scraper_class = BrowserTelegramScraper if engine_name == "browser" else FastTelegramScraper
    scraper = scraper_class(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"[cyan]در حال استخراج پست‌های کانال @{scraper.channel_username}...",
            total=config.limit,
        )

        def progress_updater(current: int, total: int):
            progress.update(task, completed=current, total=total)

        result = await scraper.scrape(progress_callback=progress_updater)

    return result


async def interactive_wizard():
    """Run interactive question-answer wizard for users who run python main.py directly."""
    print_banner()

    channel_input = Prompt.ask("[bold green]👉 آدرس یا شناسه کانال تلگرام را وارد کنید[/bold green]\n(مثال: https://t.me/durov یا @telegram یا فقط نام کاربری)")
    if not channel_input.strip():
        console.print("[red]❌ خطا: شناسه کانال نمی‌تواند خالی باشد.[/red]")
        return

    limit = IntPrompt.ask("[bold green]📊 تعداد آخرین پست‌ها جهت استخراج[/bold green]", default=20)

    console.print("\n[bold yellow]⚙️ انتخاب موتور استخراج:[/bold yellow]")
    console.print("  [cyan]1[/cyan] - مرورگر واقعی Playwright (نمایش تعاملی یا پشت صحنه، بسیار مطمئن)")
    console.print("  [cyan]2[/cyan] - موتور سریع HTTPX (سرعت فوق‌العاده بالا، بدون مصرف حافظه مرورگر)")
    engine_choice = Prompt.ask("انتخاب شما", choices=["1", "2"], default="1")
    engine_name = "browser" if engine_choice == "1" else "fast"

    headless = True
    if engine_name == "browser":
        show_browser = Confirm.ask("آیا مایلید پنجره مرورگر هنگام استخراج باز و قابل مشاهده باشد؟", default=False)
        headless = not show_browser

    download_media = Confirm.ask("آیا تصاویر و رسانه‌های پست‌ها نیز دانلود شوند؟", default=False)

    proxy_input = Prompt.ask("آدرس پروکسی در صورت نیاز (Enter برای رد شدن، مثل socks5://127.0.0.1:10808)", default="")
    proxy = proxy_input.strip() if proxy_input.strip() else None

    formats_input = Prompt.ask(
        "فرمت‌های خروجی مورد نظر (جدا شده با کاما: json, excel, csv یا all)",
        default="json, excel",
    )
    selected_formats = [f.strip().lower() for f in formats_input.replace("،", ",").split(",")]
    if "all" in selected_formats:
        selected_formats = ["json", "excel", "csv"]

    config = ScraperConfig(
        channel=channel_input,
        limit=limit,
        proxy=proxy,
        headless=headless,
        download_media=download_media,
        output_formats=selected_formats,
    )

    console.print(f"\n[bold green]🚀 شروع عملیات اسکرپینگ با موتور {engine_name}...[/bold green]\n")

    try:
        result = await run_scraper(config, engine_name=engine_name)
    except Exception as e:
        console.print(f"[bold red]❌ خطا در حین اسکرپینگ:[/bold red] {e}")
        return

    # Display results
    console.print("\n")
    display_channel_summary(result)
    console.print("\n")
    display_posts_preview(result)

    # Exporters
    exporter = DataExporter(result, output_dir=config.output_dir, proxy=config.proxy)
    generated_files = []

    if "json" in selected_formats:
        json_path = exporter.export_json()
        generated_files.append(("JSON", json_path))

    if "excel" in selected_formats or "xlsx" in selected_formats:
        xlsx_path = exporter.export_excel()
        generated_files.append(("Excel (.xlsx)", xlsx_path))

    if "csv" in selected_formats:
        csv_path = exporter.export_csv()
        generated_files.append(("CSV (UTF-8 BOM)", csv_path))

    if download_media:
        with console.status("[cyan]در حال دانلود رسانه‌ها...[/cyan]"):
            cnt = await exporter.download_media_files()
            console.print(f"[green]✅ تعداد {cnt} فایل رسانه‌ای با موفقیت در پوشه {config.output_dir}/{result.channel.username}_media ذخیره شد.[/green]")

    # Print summary panel
    console.print("\n")
    files_msg = "\n".join([f"  • [bold cyan]{fmt}:[/bold cyan] [underline]{path}[/underline]" for fmt, path in generated_files])
    console.print(
        Panel(
            f"[bold green]عملیات با موفقیت به پایان رسید![/bold green]\n\n[yellow]فایل‌های خروجی تولید شده:[/yellow]\n{files_msg}",
            title="🎉 پایان موفقیت‌آمیز",
            border_style="green",
        )
    )


async def main():
    parser = argparse.ArgumentParser(
        description="Telegram Channel Professional Web Scraper (پایتون اسکرپر کانال‌های تلگرام)",
    )
    parser.add_argument("-c", "--channel", help="Telegram channel username or URL (e.g., https://t.me/durov or @durov)")
    parser.add_argument("-l", "--limit", type=int, default=20, help="Number of latest posts to scrape (default: 20)")
    parser.add_argument("-e", "--engine", choices=["browser", "fast"], default="browser", help="Scraper engine: 'browser' (Playwright) or 'fast' (HTTPX)")
    parser.add_argument("--headed", action="store_true", help="Open browser with UI visible (for browser engine)")
    parser.add_argument("-f", "--format", default="json,excel", help="Output formats separated by comma: json,excel,csv or all")
    parser.add_argument("-d", "--download-media", action="store_true", help="Download media (photos, video thumbnails) locally")
    parser.add_argument("-p", "--proxy", default=None, help="Proxy address (e.g., http://127.0.0.1:10809 or socks5://127.0.0.1:10808)")
    parser.add_argument("-o", "--output-dir", default="downloads", help="Directory to save exported files (default: downloads)")

    args = parser.parse_args()

    # If no arguments provided, launch interactive wizard
    if not args.channel:
        await interactive_wizard()
        return

    # CLI mode
    print_banner()
    formats = [f.strip().lower() for f in args.format.split(",")]
    if "all" in formats:
        formats = ["json", "excel", "csv"]

    config = ScraperConfig(
        channel=args.channel,
        limit=args.limit,
        proxy=args.proxy,
        headless=not args.headed,
        download_media=args.download_media,
        output_formats=formats,
        output_dir=args.output_dir,
    )

    console.print(f"[cyan]شروع اسکرپ کانال [bold]{args.channel}[/bold] با موتور [bold]{args.engine}[/bold] (تعداد: {args.limit})...[/cyan]")

    try:
        result = await run_scraper(config, engine_name=args.engine)
    except Exception as e:
        console.print(f"[bold red]❌ خطا در حین اسکرپینگ:[/bold red] {e}")
        sys.exit(1)

    console.print("\n")
    display_channel_summary(result)
    console.print("\n")
    display_posts_preview(result)

    exporter = DataExporter(result, output_dir=config.output_dir, proxy=config.proxy)
    generated_files = []

    if "json" in formats:
        json_path = exporter.export_json()
        generated_files.append(("JSON", json_path))

    if "excel" in formats or "xlsx" in formats:
        xlsx_path = exporter.export_excel()
        generated_files.append(("Excel (.xlsx)", xlsx_path))

    if "csv" in formats:
        csv_path = exporter.export_csv()
        generated_files.append(("CSV (UTF-8 BOM)", csv_path))

    if args.download_media:
        with console.status("[cyan]در حال دانلود رسانه‌ها...[/cyan]"):
            cnt = await exporter.download_media_files()
            console.print(f"[green]✅ تعداد {cnt} فایل رسانه‌ای ذخیره شد.[/green]")

    console.print("\n")
    files_msg = "\n".join([f"  • [bold cyan]{fmt}:[/bold cyan] [underline]{path}[/underline]" for fmt, path in generated_files])
    console.print(
        Panel(
            f"[bold green]عملیات با موفقیت به پایان رسید![/bold green]\n\n[yellow]فایل‌های ذخیره‌شده:[/yellow]\n{files_msg}",
            title="🎉 پایان موفقیت‌آمیز",
            border_style="green",
        )
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]عملیات توسط کاربر متوقف شد.[/yellow]")
        sys.exit(0)
