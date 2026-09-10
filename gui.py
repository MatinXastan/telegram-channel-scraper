import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import webbrowser
from pathlib import Path
from typing import Optional, List

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextEdit,
    QTabWidget,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QIcon, QColor

from telegram_scraper.config import ScraperConfig
from telegram_scraper.fast_engine import FastTelegramScraper
from telegram_scraper.browser_engine import BrowserTelegramScraper
from telegram_scraper.exporter import DataExporter
from telegram_scraper.models import ScrapeResult, TelegramPost
from telegram_scraper.utils import clean_channel_username


# -------------------------------------------------------------
# Modern Dark QSS Theme
# -------------------------------------------------------------
MODERN_STYLE = """
QMainWindow {
    background-color: #0f172a;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
}
QGroupBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 12px;
    font-weight: bold;
    color: #38bdf8;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top right;
    padding: 0 8px;
    color: #38bdf8;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #0f172a;
    border: 1px solid #475569;
    border-radius: 6px;
    padding: 6px 10px;
    color: #f8fafc;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QCheckBox {
    spacing: 8px;
    color: #cbd5e1;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #0f172a;
}
QCheckBox::indicator:checked {
    background-color: #0284c7;
    border: 1px solid #38bdf8;
}
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    min-height: 22px;
}
QPushButton:hover {
    background-color: #1d4ed8;
}
QPushButton:pressed {
    background-color: #1e40af;
}
QPushButton:disabled {
    background-color: #334155;
    color: #64748b;
}
QPushButton#btn_start {
    background-color: #059669;
    font-size: 14px;
}
QPushButton#btn_start:hover {
    background-color: #047857;
}
QPushButton#btn_stop {
    background-color: #dc2626;
}
QPushButton#btn_stop:hover {
    background-color: #b91c1c;
}
QProgressBar {
    border: 1px solid #334155;
    border-radius: 6px;
    background-color: #0f172a;
    text-align: center;
    color: #f8fafc;
    font-weight: bold;
    height: 18px;
}
QProgressBar::chunk {
    background-color: #0284c7;
    border-radius: 5px;
}
QTableWidget {
    background-color: #1e293b;
    alternate-background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 8px;
    gridline-color: #334155;
    color: #f1f5f9;
}
QTableWidget::item:selected {
    background-color: #0369a1;
}
QHeaderView::section {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 6px;
    font-weight: bold;
    border: 1px solid #334155;
}
QTabWidget::pane {
    border: 1px solid #334155;
    border-radius: 8px;
    background-color: #1e293b;
}
QTabBar::tab {
    background-color: #0f172a;
    color: #94a3b8;
    padding: 8px 16px;
    margin-right: 4px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    background-color: #1e293b;
    color: #38bdf8;
    font-weight: bold;
}
QTextEdit {
    background-color: #0f172a;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #e2e8f0;
    padding: 8px;
}
"""


# -------------------------------------------------------------
# Worker Thread for Non-Blocking Async Scraping
# -------------------------------------------------------------
class ScraperWorker(QThread):
    """Executes the scraping workflow in a separate background thread."""

    progress_signal = Signal(int, int, str)
    log_signal = Signal(str)
    finished_signal = Signal(object, list)  # (ScrapeResult, list of generated files)
    error_signal = Signal(str)

    def __init__(self, config: ScraperConfig, engine_name: str):
        super().__init__()
        self.config = config
        self.engine_name = engine_name
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._execute_scraping())
            loop.close()
        except Exception as e:
            self.error_signal.emit(str(e))

    async def _execute_scraping(self):
        self.log_signal.emit(f"🚀 شروع استخراج از کانال @{self.config.channel} با موتور {self.engine_name}...")

        scraper_class = BrowserTelegramScraper if self.engine_name == "browser" else FastTelegramScraper
        scraper = scraper_class(self.config)

        def progress_callback(current: int, total: int):
            if self._is_cancelled:
                raise RuntimeError("عملیات توسط کاربر متوقف شد.")
            pct = int((current / max(total, 1)) * 100)
            self.progress_signal.emit(current, total, f"استخراج {current} از {total} پست ({pct}%)")

        result: ScrapeResult = await scraper.scrape(progress_callback=progress_callback)

        self.log_signal.emit(f"✅ استخراج پست‌ها تکمیل شد. تعداد: {result.total_scraped}")
        self.log_signal.emit("💾 در حال تولید فایل‌های خروجی...")

        exporter = DataExporter(
            result,
            output_dir=self.config.output_dir,
            proxy=self.config.proxy,
        )
        generated_files = []

        if "excel" in self.config.output_formats or "xlsx" in self.config.output_formats:
            xlsx_path = exporter.export_excel()
            generated_files.append(("Excel", xlsx_path))
            self.log_signal.emit(f"📄 فایل اکسل ذخیره شد: {xlsx_path}")

        if "json" in self.config.output_formats:
            json_path = exporter.export_json()
            generated_files.append(("JSON", json_path))
            self.log_signal.emit(f"📄 فایل JSON ذخیره شد: {json_path}")

        if "csv" in self.config.output_formats:
            csv_path = exporter.export_csv()
            generated_files.append(("CSV", csv_path))
            self.log_signal.emit(f"📄 فایل CSV ذخیره شد: {csv_path}")

        if self.config.download_media:
            self.log_signal.emit("📥 در حال دانلود رسانه‌ها و تصاویر...")
            count = await exporter.download_media_files()
            self.log_signal.emit(f"✅ تعداد {count} فایل رسانه‌ای با موفقیت دانلود شد.")

        self.finished_signal.emit(result, generated_files)


# -------------------------------------------------------------
# Main GUI Window
# -------------------------------------------------------------
class TelegramScraperApp(QMainWindow):
    """Main window for the Telegram Channel Scraper GUI."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Telegram Channel Web Scraper — اسکرپر حرفه‌ای کانال‌های تلگرام")
        self.resize(1150, 750)
        self.setMinimumSize(950, 600)
        self.setStyleSheet(MODERN_STYLE)

        self.worker: Optional[ScraperWorker] = None
        self.current_result: Optional[ScrapeResult] = None
        self.generated_files: List[tuple] = []

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #1e293b; border-radius: 8px; padding: 6px;")
        h_layout = QVBoxLayout(header_frame)
        title_label = QLabel("🚀 Telegram Web Scraper")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        subtitle_label = QLabel("استخراج پیشرفته پست‌ها و رسانه‌های تلگرام")
        subtitle_label.setStyleSheet("font-size: 11px; color: #94a3b8;")
        h_layout.addWidget(title_label)
        h_layout.addWidget(subtitle_label)
        left_layout.addWidget(header_frame)

        target_group = QGroupBox("🎯 کانال مورد نظر (Channel)")
        tg_layout = QVBoxLayout(target_group)
        self.input_channel = QLineEdit()
        self.input_channel.setPlaceholderText("https://t.me/durov یا @username یا username")
        tg_layout.addWidget(self.input_channel)
        left_layout.addWidget(target_group)

        config_group = QGroupBox("⚙️ تنظیمات استخراج (Options)")
        cfg_layout = QGridLayout(config_group)
        cfg_layout.setSpacing(8)

        cfg_layout.addWidget(QLabel("تعداد آخرین پست‌ها:"), 0, 0)
        self.spin_limit = QSpinBox()
        self.spin_limit.setRange(1, 500)
        self.spin_limit.setValue(20)
        cfg_layout.addWidget(self.spin_limit, 0, 1)

        cfg_layout.addWidget(QLabel("موتور استخراج:"), 1, 0)
        self.combo_engine = QComboBox()
        self.combo_engine.addItem("Playwright (مرورگر واقعی)", "browser")
        self.combo_engine.addItem("Fast HTTPX (موتور پرسرعت)", "fast")
        self.combo_engine.currentIndexChanged.connect(self._on_engine_changed)
        cfg_layout.addWidget(self.combo_engine, 1, 1)

        self.chk_headed = QCheckBox("نمایش پنجره مرورگر (Headed)")
        self.chk_headed.setChecked(False)
        cfg_layout.addWidget(self.chk_headed, 2, 0, 1, 2)

        self.chk_download_media = QCheckBox("دانلود خودکار تصاویر و رسانه‌ها")
        self.chk_download_media.setChecked(False)
        cfg_layout.addWidget(self.chk_download_media, 3, 0, 1, 2)

        cfg_layout.addWidget(QLabel("پروکسی (اختیاری):"), 4, 0)
        self.input_proxy = QLineEdit()
        self.input_proxy.setPlaceholderText("مثال: socks5://127.0.0.1:10808")
        cfg_layout.addWidget(self.input_proxy, 4, 1)

        left_layout.addWidget(config_group)

        export_group = QGroupBox("📁 فرمت‌های خروجی و مسیر ذخیره")
        exp_layout = QVBoxLayout(export_group)

        fmt_layout = QHBoxLayout()
        self.chk_excel = QCheckBox("Excel (.xlsx)")
        self.chk_excel.setChecked(True)
        self.chk_json = QCheckBox("JSON")
        self.chk_json.setChecked(True)
        self.chk_csv = QCheckBox("CSV")
        self.chk_csv.setChecked(False)
        fmt_layout.addWidget(self.chk_excel)
        fmt_layout.addWidget(self.chk_json)
        fmt_layout.addWidget(self.chk_csv)
        exp_layout.addLayout(fmt_layout)

        dir_layout = QHBoxLayout()
        self.input_outdir = QLineEdit("downloads")
        self.btn_browse = QPushButton("انتخاب مسیر...")
        self.btn_browse.clicked.connect(self._browse_output_dir)
        dir_layout.addWidget(self.input_outdir)
        dir_layout.addWidget(self.btn_browse)
        exp_layout.addLayout(dir_layout)

        left_layout.addWidget(export_group)

        action_layout = QHBoxLayout()
        self.btn_start = QPushButton("🚀 شروع استخراج")
        self.btn_start.setObjectName("btn_start")
        self.btn_start.clicked.connect(self._start_scraping)

        self.btn_stop = QPushButton("⏹️ توقف")
        self.btn_stop.setObjectName("btn_stop")
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._stop_scraping)

        action_layout.addWidget(self.btn_start)
        action_layout.addWidget(self.btn_stop)
        left_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        left_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("آماده به کار")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #94a3b8; font-size: 11px;")
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        left_container.setFixedWidth(360)
        splitter.addWidget(left_container)

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.card_channel = QFrame()
        self.card_channel.setStyleSheet(
            "background-color: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 10px;"
        )
        card_layout = QVBoxLayout(self.card_channel)
        card_top = QHBoxLayout()

        self.lbl_ch_title = QLabel("هنوز کانالی استخراج نشده است")
        self.lbl_ch_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        self.lbl_ch_subs = QLabel("-")
        self.lbl_ch_subs.setStyleSheet(
            "background-color: #0284c7; color: #ffffff; padding: 2px 8px; border-radius: 10px; font-weight: bold;"
        )
        self.lbl_ch_verified = QLabel("")

        card_top.addWidget(self.lbl_ch_title)
        card_top.addWidget(self.lbl_ch_subs)
        card_top.addWidget(self.lbl_ch_verified)
        card_top.addStretch()
        card_layout.addLayout(card_top)

        self.lbl_ch_desc = QLabel("برای شروع، آدرس یک کانال تلگرام را وارد کرده و روی 'شروع استخراج' کلیک کنید.")
        self.lbl_ch_desc.setWordWrap(True)
        self.lbl_ch_desc.setStyleSheet("color: #94a3b8; font-size: 12px; margin-top: 4px;")
        card_layout.addWidget(self.lbl_ch_desc)

        right_layout.addWidget(self.card_channel)

        self.tabs = QTabWidget()

        tab_posts = QWidget()
        tab_posts_layout = QVBoxLayout(tab_posts)
        tab_posts_layout.setContentsMargins(6, 6, 6, 6)

        posts_splitter = QSplitter(Qt.Orientation.Vertical)

        self.table_posts = QTableWidget()
        self.table_posts.setColumnCount(6)
        self.table_posts.setHorizontalHeaderLabels(["شناسه (ID)", "تاریخ", "بازدید", "واکنش‌ها", "نوع رسانه", "خلاصه متن"])
        self.table_posts.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table_posts.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_posts.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table_posts.itemSelectionChanged.connect(self._on_post_selected)
        posts_splitter.addWidget(self.table_posts)

        detail_box = QGroupBox("🔍 مشاهده متن و جزئیات پست انتخاب‌شده")
        d_layout = QVBoxLayout(detail_box)

        self.txt_post_detail = QTextEdit()
        self.txt_post_detail.setReadOnly(True)
        self.txt_post_detail.setPlaceholderText("روی هر سطر از جدول بالا کلیک کنید تا متن کامل و اطلاعات آن در اینجا نمایش داده شود.")
        d_layout.addWidget(self.txt_post_detail)

        detail_action_layout = QHBoxLayout()
        self.btn_open_post_web = QPushButton("🌐 مشاهده پست در وب / تلگرام")
        self.btn_open_post_web.setEnabled(False)
        self.btn_open_post_web.clicked.connect(self._open_selected_post_in_browser)
        detail_action_layout.addStretch()
        detail_action_layout.addWidget(self.btn_open_post_web)
        d_layout.addLayout(detail_action_layout)

        posts_splitter.addWidget(detail_box)
        posts_splitter.setSizes([320, 200])

        tab_posts_layout.addWidget(posts_splitter)
        self.tabs.addTab(tab_posts, "📋 لیست پست‌ها (Posts)")

        tab_logs = QWidget()
        tab_logs_layout = QVBoxLayout(tab_logs)
        tab_logs_layout.setContentsMargins(6, 6, 6, 6)

        files_bar = QHBoxLayout()
        self.btn_open_folder = QPushButton("📂 باز کردن پوشه دانلودها")
        self.btn_open_folder.clicked.connect(self._open_output_folder)
        self.btn_open_excel = QPushButton("📊 باز کردن فایل اکسل")
        self.btn_open_excel.setEnabled(False)
        self.btn_open_excel.clicked.connect(self._open_excel_file)
        self.btn_open_json = QPushButton("📄 باز کردن فایل JSON")
        self.btn_open_json.setEnabled(False)
        self.btn_open_json.clicked.connect(self._open_json_file)

        files_bar.addWidget(self.btn_open_folder)
        files_bar.addWidget(self.btn_open_excel)
        files_bar.addWidget(self.btn_open_json)
        files_bar.addStretch()
        tab_logs_layout.addLayout(files_bar)

        self.txt_logs = QTextEdit()
        self.txt_logs.setReadOnly(True)
        tab_logs_layout.addWidget(self.txt_logs)

        self.tabs.addTab(tab_logs, "📝 لاگ‌ها و گزارش عملیات (Logs)")

        right_layout.addWidget(self.tabs)
        splitter.addWidget(right_container)

        splitter.setSizes([360, 790])
        main_layout.addWidget(splitter)

    def _on_engine_changed(self, index: int):
        is_browser = self.combo_engine.currentData() == "browser"
        self.chk_headed.setEnabled(is_browser)
        if not is_browser:
            self.chk_headed.setChecked(False)

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "انتخاب پوشه ذخیره‌سازی", self.input_outdir.text())
        if folder:
            self.input_outdir.setText(folder)

    def _start_scraping(self):
        raw_channel = self.input_channel.text().strip()
        channel = clean_channel_username(raw_channel)
        if not channel:
            QMessageBox.warning(self, "خطا", "لطفاً آدرس یا شناسه کانال تلگرام را به درستی وارد کنید.")
            return

        formats = []
        if self.chk_excel.isChecked():
            formats.append("excel")
        if self.chk_json.isChecked():
            formats.append("json")
        if self.chk_csv.isChecked():
            formats.append("csv")

        if not formats:
            QMessageBox.warning(self, "خطا", "حداقل یکی از فرمت‌های خروجی (Excel, JSON, CSV) را انتخاب کنید.")
            return

        engine_name = self.combo_engine.currentData()
        headed = self.chk_headed.isChecked()
        download_media = self.chk_download_media.isChecked()
        proxy = self.input_proxy.text().strip() or None
        limit = self.spin_limit.value()
        out_dir = self.input_outdir.text().strip() or "downloads"

        config = ScraperConfig(
            channel=channel,
            limit=limit,
            proxy=proxy,
            headless=not headed,
            download_media=download_media,
            output_formats=formats,
            output_dir=out_dir,
        )

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setValue(0)
        self.lbl_status.setText("در حال اتصال به تلگرام...")
        self.txt_logs.clear()
        self.table_posts.setRowCount(0)
        self.txt_post_detail.clear()
        self.btn_open_post_web.setEnabled(False)

        self.worker = ScraperWorker(config, engine_name=engine_name)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.log_signal.connect(self._append_log)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _stop_scraping(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.lbl_status.setText("در حال توقف عملیات...")
            self.btn_stop.setEnabled(False)

    @Slot(int, int, str)
    def _on_progress(self, current: int, total: int, message: str):
        pct = int((current / max(total, 1)) * 100)
        self.progress_bar.setValue(min(pct, 100))
        self.lbl_status.setText(message)

    @Slot(str)
    def _append_log(self, text: str):
        self.txt_logs.append(text)

    @Slot(object, list)
    def _on_finished(self, result: ScrapeResult, generated_files: list):
        self.current_result = result
        self.generated_files = generated_files
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.progress_bar.setValue(100)
        self.lbl_status.setText(f"عملیات با موفقیت انجام شد! ({result.total_scraped} پست)")

        ch = result.channel
        self.lbl_ch_title.setText(f"{ch.title} (@{ch.username})")
        self.lbl_ch_subs.setText(f"اعضا: {ch.subscribers or 'نامشخص'}")
        self.lbl_ch_verified.setText("✅ رسمی" if ch.is_verified else "")
        self.lbl_ch_desc.setText(ch.description or "فاقد توضیحات")

        self.table_posts.setRowCount(len(result.posts))
        for row, post in enumerate(result.posts):
            item_id = QTableWidgetItem(str(post.id))
            item_id.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_val = post.date_formatted or post.date_iso or "-"
            item_date = QTableWidgetItem(date_val[:16])
            item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_views = QTableWidgetItem(post.views or "-")
            item_views.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            rx_str = f"{post.total_reactions_count}" if post.total_reactions_count else "-"
            item_rx = QTableWidgetItem(rx_str)
            item_rx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            media_types = ", ".join(set(m.type for m in post.media)) or "-"
            item_media = QTableWidgetItem(media_types)
            item_media.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            preview_text = post.text.replace("\n", " ")[:90] if post.text else "[فاقد متن]"
            item_text = QTableWidgetItem(preview_text)
            self.table_posts.setItem(row, 0, item_id)
            self.table_posts.setItem(row, 1, item_date)
            self.table_posts.setItem(row, 2, item_views)
            self.table_posts.setItem(row, 3, item_rx)
            self.table_posts.setItem(row, 4, item_media)
            self.table_posts.setItem(row, 5, item_text)

        for fmt, path in generated_files:
            if fmt == "Excel":
                self.btn_open_excel.setEnabled(True)
            elif fmt == "JSON":
                self.btn_open_json.setEnabled(True)

        self.tabs.setCurrentIndex(0)
        QMessageBox.information(
            self,
            "پایان موفقیت‌آمیز",
            f"تعداد {result.total_scraped} پست از کانال @{ch.username} با موفقیت استخراج و ذخیره شد.",
        )

    @Slot(str)
    def _on_error(self, err_msg: str):
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("خطا در عملیات!")
        self.txt_logs.append(f"❌ خطا: {err_msg}")
        QMessageBox.critical(self, "خطا در اسکرپینگ", f"خطایی رخ داد:\n{err_msg}")

    def _on_post_selected(self):
        selected_rows = self.table_posts.selectionModel().selectedRows()
        if not selected_rows or not self.current_result:
            self.btn_open_post_web.setEnabled(False)
            return

        row = selected_rows[0].row()
        post: TelegramPost = self.current_result.posts[row]

        details = []
        details.append(f"📌 شناسه پست (ID): {post.id}")
        details.append(f"📅 تاریخ انتشار: {post.date_iso or post.date_formatted or 'نامشخص'}")
        details.append(f"👁️ بازدیدها: {post.views or 'نامشخص'}")
        details.append(f"🔗 آدرس مستقیم: {post.url}")

        if post.is_pinned:
            details.append("📌 این پست در کانال پین شده است.")
        if post.is_forwarded and post.forward_info:
            details.append(f"↪️ بازنشر از: {post.forward_info.from_name} ({post.forward_info.from_url or ''})")

        if post.reactions:
            rx_list = ", ".join(f"{r.emoji} {r.count}" for r in post.reactions)
            details.append(f"❤️ واکنش‌ها: {rx_list}")

        if post.media:
            m_list = [f"{m.type}: {m.url or m.thumbnail_url or m.file_name or ''}" for m in post.media]
            details.append("🖼️ رسانه‌ها:\n  • " + "\n  • ".join(m_list))

        if post.link_preview:
            details.append(f"🌐 پیش‌نمایش لینک: {post.link_preview.title} ({post.link_preview.url})")

        details.append("\n" + "=" * 50 + "\nمتن کامل پیام:\n" + "=" * 50)
        details.append(post.text if post.text else "[این پیام صرفاً حاوی رسانه یا فاقد متن است]")

        self.txt_post_detail.setPlainText("\n".join(details))
        self.btn_open_post_web.setEnabled(True)

    def _open_selected_post_in_browser(self):
        selected_rows = self.table_posts.selectionModel().selectedRows()
        if selected_rows and self.current_result:
            row = selected_rows[0].row()
            url = self.current_result.posts[row].url
            webbrowser.open(url)

    def _open_output_folder(self):
        folder = Path(self.input_outdir.text().strip() or "downloads")
        folder.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(folder)
        else:
            webbrowser.open(folder.as_uri())

    def _open_excel_file(self):
        for fmt, path in self.generated_files:
            if fmt == "Excel" and os.path.exists(path):
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    webbrowser.open(Path(path).as_uri())
                return

    def _open_json_file(self):
        for fmt, path in self.generated_files:
            if fmt == "JSON" and os.path.exists(path):
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    webbrowser.open(Path(path).as_uri())
                return


def main():
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = TelegramScraperApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
