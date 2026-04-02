from __future__ import annotations

import sys
from pathlib import Path
from urllib.request import urlopen

from PySide6.QtCore import QThread, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.core.download_worker import DownloadWorker
from src.core.ffmpeg_utils import ffmpeg_exists
from src.core.models import DownloadOptions, VideoInfo
from src.core.utils import format_seconds, parse_time_to_seconds
from src.core.youtube_service import YouTubeService
from src.ui.range_slider import DualRangeSlider


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("YouTube Segment Downloader")
        self.resize(980, 700)

        self.video_info: VideoInfo | None = None
        self.download_thread: QThread | None = None
        self.download_worker: DownloadWorker | None = None

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self._update_trim_labels(0, 0)
        self._set_controls_enabled(False)
        self.whole_video_radio.setChecked(True)
        self._sync_mode_controls()

        if not ffmpeg_exists():
            QMessageBox.warning(
                self,
                "ffmpeg not found",
                "ffmpeg and ffprobe were not found in PATH. The app can open, but downloading will fail until ffmpeg is installed.",
            )

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(18)

        header = QLabel("YouTube Segment Downloader")
        header.setObjectName("headerTitle")
        subtitle = QLabel("Fetch a YouTube video, choose a time range, and download only the part you need.")
        subtitle.setObjectName("subtitle")
        root.addWidget(header)
        root.addWidget(subtitle)

        url_card = QFrame()
        url_card.setObjectName("card")
        url_layout = QHBoxLayout(url_card)
        url_layout.setContentsMargins(18, 18, 18, 18)
        url_layout.setSpacing(12)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste a YouTube link here...")
        self.fetch_button = QPushButton("Fetch Info")
        self.fetch_button.setMinimumWidth(140)
        url_layout.addWidget(self.url_input, 1)
        url_layout.addWidget(self.fetch_button)
        root.addWidget(url_card)

        info_grid = QGridLayout()
        info_grid.setSpacing(18)
        root.addLayout(info_grid)

        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(18, 18, 18, 18)
        info_layout.setSpacing(12)

        info_title = QLabel("Video Information")
        info_title.setObjectName("sectionTitle")
        info_layout.addWidget(info_title)

        self.thumbnail_label = QLabel("No thumbnail")
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        self.thumbnail_label.setFixedSize(320, 180)
        self.thumbnail_label.setObjectName("thumbnail")
        info_layout.addWidget(self.thumbnail_label, alignment=Qt.AlignLeft)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignLeft)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(10)

        self.title_value = QLabel("-")
        self.duration_value = QLabel("-")
        self.uploader_value = QLabel("-")
        self.resolution_value = QLabel("-")

        form.addRow("Title:", self.title_value)
        form.addRow("Duration:", self.duration_value)
        form.addRow("Uploader:", self.uploader_value)
        form.addRow("Resolution:", self.resolution_value)
        info_layout.addLayout(form)
        info_grid.addWidget(info_card, 0, 0)

        config_card = QFrame()
        config_card.setObjectName("card")
        config_layout = QVBoxLayout(config_card)
        config_layout.setContentsMargins(18, 18, 18, 18)
        config_layout.setSpacing(16)

        trim_group = QGroupBox("Trim Selection")
        trim_layout = QVBoxLayout(trim_group)

        range_mode_layout = QHBoxLayout()
        self.whole_video_radio = QRadioButton("Download full video")
        self.custom_range_radio = QRadioButton("Download selected range")
        range_mode_layout.addWidget(self.whole_video_radio)
        range_mode_layout.addWidget(self.custom_range_radio)
        range_mode_layout.addStretch(1)
        trim_layout.addLayout(range_mode_layout)

        self.range_slider = DualRangeSlider()
        trim_layout.addWidget(self.range_slider)

        trim_values_layout = QGridLayout()
        self.start_input = QLineEdit("00:00")
        self.end_input = QLineEdit("00:00")
        self.start_label = QLabel("Start: 00:00")
        self.end_label = QLabel("End: 00:00")
        self.selection_label = QLabel("Selection length: 00:00")

        trim_values_layout.addWidget(QLabel("Start"), 0, 0)
        trim_values_layout.addWidget(self.start_input, 0, 1)
        trim_values_layout.addWidget(self.start_label, 0, 2)
        trim_values_layout.addWidget(QLabel("End"), 1, 0)
        trim_values_layout.addWidget(self.end_input, 1, 1)
        trim_values_layout.addWidget(self.end_label, 1, 2)
        trim_values_layout.addWidget(self.selection_label, 2, 0, 1, 3)
        trim_layout.addLayout(trim_values_layout)
        config_layout.addWidget(trim_group)

        mode_group = QGroupBox("Download Mode")
        mode_layout = QVBoxLayout(mode_group)
        self.video_audio_radio = QRadioButton("Video + audio")
        self.video_only_radio = QRadioButton("Video only")
        self.audio_only_radio = QRadioButton("Audio only")
        self.video_audio_radio.setChecked(True)
        mode_layout.addWidget(self.video_audio_radio)
        mode_layout.addWidget(self.video_only_radio)
        mode_layout.addWidget(self.audio_only_radio)
        config_layout.addWidget(mode_group)

        audio_group = QGroupBox("Audio Format")
        audio_layout = QHBoxLayout(audio_group)
        self.mp3_radio = QRadioButton("MP3")
        self.m4a_radio = QRadioButton("M4A")
        self.m4a_radio.setChecked(True)
        audio_layout.addWidget(self.mp3_radio)
        audio_layout.addWidget(self.m4a_radio)
        audio_layout.addStretch(1)
        config_layout.addWidget(audio_group)

        path_group = QGroupBox("Output Location")
        path_layout = QHBoxLayout(path_group)
        self.output_path_input = QLineEdit(str(Path.home() / "Downloads"))
        self.output_browse_button = QPushButton("Choose Folder")
        path_layout.addWidget(self.output_path_input, 1)
        path_layout.addWidget(self.output_browse_button)
        config_layout.addWidget(path_group)

        info_grid.addWidget(config_card, 0, 1)

        progress_card = QFrame()
        progress_card.setObjectName("card")
        progress_layout = QVBoxLayout(progress_card)
        progress_layout.setContentsMargins(18, 18, 18, 18)
        progress_layout.setSpacing(12)

        progress_title = QLabel("Download Progress")
        progress_title.setObjectName("sectionTitle")
        progress_layout.addWidget(progress_title)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_status = QLabel("Idle")
        self.speed_label = QLabel("Speed: -")
        self.eta_label = QLabel("ETA: -")
        self.percent_label = QLabel("0%")

        progress_meta = QHBoxLayout()
        progress_meta.addWidget(self.percent_label)
        progress_meta.addStretch(1)
        progress_meta.addWidget(self.speed_label)
        progress_meta.addSpacing(16)
        progress_meta.addWidget(self.eta_label)

        button_bar = QHBoxLayout()
        self.download_button = QPushButton("Download")
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setEnabled(False)
        button_bar.addWidget(self.download_button)
        button_bar.addWidget(self.cancel_button)
        button_bar.addStretch(1)

        progress_layout.addWidget(self.progress_bar)
        progress_layout.addLayout(progress_meta)
        progress_layout.addWidget(self.progress_status)
        progress_layout.addLayout(button_bar)
        root.addWidget(progress_card)
        root.addStretch(1)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QWidget {
                background: #0f1218;
                color: #f3f5f9;
                font-size: 14px;
            }
            QFrame#card, QGroupBox {
                background: #171b23;
                border: 1px solid #2a2f3a;
                border-radius: 16px;
            }
            QLabel#headerTitle {
                font-size: 28px;
                font-weight: 700;
            }
            QLabel#subtitle {
                color: #a8b0c1;
                font-size: 14px;
                margin-bottom: 4px;
            }
            QLabel#sectionTitle {
                font-size: 18px;
                font-weight: 600;
            }
            QLabel#thumbnail {
                background: #10141b;
                border: 1px dashed #344054;
                border-radius: 12px;
                color: #98a2b3;
            }
            QLineEdit {
                background: #11161f;
                border: 1px solid #2d3646;
                border-radius: 10px;
                padding: 10px 12px;
                selection-background-color: #4f8cff;
            }
            QPushButton {
                background: #4f8cff;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover { background: #6a9dff; }
            QPushButton:disabled {
                background: #2a3342;
                color: #8090a8;
            }
            QProgressBar {
                background: #11161f;
                border: 1px solid #2d3646;
                border-radius: 10px;
                text-align: center;
                min-height: 18px;
            }
            QProgressBar::chunk {
                background: #4f8cff;
                border-radius: 8px;
            }
            QGroupBox {
                margin-top: 10px;
                padding-top: 12px;
                font-weight: 600;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }
            QRadioButton {
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 16px;
                height: 16px;
            }
            """
        )

    def _connect_signals(self) -> None:
        self.fetch_button.clicked.connect(self.fetch_video_info)
        self.output_browse_button.clicked.connect(self.choose_output_dir)
        self.range_slider.values_changed.connect(self._on_slider_changed)
        self.start_input.editingFinished.connect(self._on_time_inputs_changed)
        self.end_input.editingFinished.connect(self._on_time_inputs_changed)
        self.download_button.clicked.connect(self.start_download)
        self.cancel_button.clicked.connect(self.cancel_download)
        self.audio_only_radio.toggled.connect(self._sync_mode_controls)
        self.whole_video_radio.toggled.connect(self._sync_mode_controls)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in [
            self.range_slider,
            self.start_input,
            self.end_input,
            self.video_audio_radio,
            self.video_only_radio,
            self.audio_only_radio,
            self.mp3_radio,
            self.m4a_radio,
            self.output_path_input,
            self.output_browse_button,
            self.download_button,
            self.whole_video_radio,
            self.custom_range_radio,
        ]:
            widget.setEnabled(enabled)

    def _sync_mode_controls(self) -> None:
        audio_mode = self.audio_only_radio.isChecked()
        self.mp3_radio.setEnabled(audio_mode)
        self.m4a_radio.setEnabled(audio_mode)

        custom_range = self.custom_range_radio.isChecked()
        self.range_slider.setEnabled(custom_range and self.video_info is not None)
        self.start_input.setEnabled(custom_range and self.video_info is not None)
        self.end_input.setEnabled(custom_range and self.video_info is not None)

    def choose_output_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "Choose output folder", self.output_path_input.text())
        if directory:
            self.output_path_input.setText(directory)

    def fetch_video_info(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Missing URL", "Please paste a YouTube URL first.")
            return

        self.fetch_button.setEnabled(False)
        self.progress_status.setText("Fetching video info...")
        QApplication.processEvents()
        try:
            info = YouTubeService.fetch_info(url)
            self.video_info = info
            self.title_value.setText(info.title)
            self.duration_value.setText(format_seconds(info.duration))
            self.uploader_value.setText(info.uploader)
            self.resolution_value.setText(info.resolution_text)
            self.range_slider.set_range(0, info.duration)
            self.range_slider.set_values(0, info.duration)
            self.start_input.setText("00:00")
            self.end_input.setText(format_seconds(info.duration))
            self._update_trim_labels(0, info.duration)
            self._set_controls_enabled(True)
            self._sync_mode_controls()
            self._load_thumbnail(info.thumbnail_url)
            self.progress_status.setText("Video info loaded.")
        except Exception as exc:
            QMessageBox.critical(self, "Failed to fetch info", str(exc))
            self.progress_status.setText("Failed to fetch video info.")
        finally:
            self.fetch_button.setEnabled(True)

    def _load_thumbnail(self, url: str) -> None:
        if not url:
            self.thumbnail_label.setText("No thumbnail")
            return
        try:
            data = urlopen(url, timeout=10).read()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            scaled = pixmap.scaled(self.thumbnail_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.thumbnail_label.setPixmap(scaled)
        except Exception:
            self.thumbnail_label.setText("Thumbnail unavailable")

    def _on_slider_changed(self, start: int, end: int) -> None:
        self.start_input.setText(format_seconds(start))
        self.end_input.setText(format_seconds(end))
        self._update_trim_labels(start, end)

    def _update_trim_labels(self, start: int, end: int) -> None:
        self.start_label.setText(f"Start: {format_seconds(start)}")
        self.end_label.setText(f"End: {format_seconds(end)}")
        self.selection_label.setText(f"Selection length: {format_seconds(max(0, end - start))}")

    def _on_time_inputs_changed(self) -> None:
        if self.video_info is None:
            return
        try:
            start = parse_time_to_seconds(self.start_input.text())
            end = parse_time_to_seconds(self.end_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid time", str(exc))
            return

        duration = self.video_info.duration
        start = max(0, min(start, duration))
        end = max(0, min(end, duration))
        if end < start:
            QMessageBox.warning(self, "Invalid range", "End time cannot be smaller than start time.")
            self.end_input.setText(format_seconds(max(start, end)))
            return

        self.range_slider.set_values(start, end)

    def _selected_output_mode(self) -> str:
        if self.audio_only_radio.isChecked():
            return "audio_only"
        if self.video_only_radio.isChecked():
            return "video_only"
        return "video_audio"

    def _selected_audio_format(self) -> str:
        return "mp3" if self.mp3_radio.isChecked() else "m4a"

    def start_download(self) -> None:
        if self.video_info is None:
            QMessageBox.warning(self, "No video loaded", "Please fetch video information first.")
            return

        output_dir = Path(self.output_path_input.text().strip())
        if not output_dir:
            QMessageBox.warning(self, "Missing output folder", "Please choose an output folder.")
            return

        try:
            start_seconds = parse_time_to_seconds(self.start_input.text())
            end_seconds = parse_time_to_seconds(self.end_input.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid time", str(exc))
            return

        if end_seconds < start_seconds:
            QMessageBox.warning(self, "Invalid range", "End time cannot be smaller than start time.")
            return

        full_download = self.whole_video_radio.isChecked()
        if not full_download and start_seconds == end_seconds:
            QMessageBox.warning(self, "Invalid selection", "Selected range must be longer than zero seconds.")
            return

        options = DownloadOptions(
            url=self.video_info.url,
            output_dir=output_dir,
            output_mode=self._selected_output_mode(),
            audio_format=self._selected_audio_format(),
            start_seconds=None if full_download else start_seconds,
            end_seconds=None if full_download else end_seconds,
            full_download=full_download,
            title_hint=self.video_info.title,
        )

        self.progress_bar.setValue(0)
        self.percent_label.setText("0%")
        self.speed_label.setText("Speed: -")
        self.eta_label.setText("ETA: -")
        self.progress_status.setText("Starting download...")

        self.download_thread = QThread(self)
        self.download_worker = DownloadWorker(options)
        self.download_worker.moveToThread(self.download_thread)

        self.download_thread.started.connect(self.download_worker.run)
        self.download_worker.progress_changed.connect(self._on_progress_changed)
        self.download_worker.status_changed.connect(self.progress_status.setText)
        self.download_worker.finished.connect(self._on_download_finished)
        self.download_worker.failed.connect(self._on_download_failed)
        self.download_worker.cancelled.connect(self._on_download_cancelled)

        self.download_worker.finished.connect(self.download_thread.quit)
        self.download_worker.failed.connect(self.download_thread.quit)
        self.download_worker.cancelled.connect(self.download_thread.quit)
        self.download_thread.finished.connect(self.download_worker.deleteLater)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        self.download_thread.finished.connect(self._clear_download_refs)

        self.download_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.fetch_button.setEnabled(False)
        self.download_thread.start()

    def cancel_download(self) -> None:
        if self.download_worker is not None:
            self.download_worker.request_cancel()
            self.progress_status.setText("Cancelling...")
            self.cancel_button.setEnabled(False)

    def _clear_download_refs(self) -> None:
        self.download_worker = None
        self.download_thread = None
        self.download_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.fetch_button.setEnabled(True)

    def _on_progress_changed(self, percent: float, speed: str, eta: str, status: str) -> None:
        self.progress_bar.setValue(int(percent))
        self.percent_label.setText(f"{percent:.1f}%")
        self.speed_label.setText(f"Speed: {speed}")
        self.eta_label.setText(f"ETA: {eta}")
        self.progress_status.setText(status.capitalize())

    def _on_download_finished(self, path: str) -> None:
        self.progress_bar.setValue(100)
        self.percent_label.setText("100%")
        self.progress_status.setText("Completed successfully.")
        QMessageBox.information(self, "Download complete", f"Saved to:\n{path}")

    def _on_download_failed(self, message: str) -> None:
        self.progress_status.setText("Failed.")
        QMessageBox.critical(self, "Download failed", message)

    def _on_download_cancelled(self, message: str) -> None:
        self.progress_status.setText("Cancelled.")
        QMessageBox.information(self, "Cancelled", message)


def run_app() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("YouTube Segment Downloader")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
