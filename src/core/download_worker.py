from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot
from yt_dlp import DownloadError, YoutubeDL

from .ffmpeg_utils import convert_audio, ffmpeg_exists, trim_media, FFmpegError
from .models import DownloadOptions
from .utils import ensure_unique_path, sanitize_filename


class UserCancelledError(RuntimeError):
    pass


class DownloadWorker(QObject):
    progress_changed = Signal(float, str, str, str)  # percent, speed, eta, status
    status_changed = Signal(str)
    finished = Signal(str)
    failed = Signal(str)
    cancelled = Signal(str)

    def __init__(self, options: DownloadOptions) -> None:
        super().__init__()
        self.options = options
        self._cancel_requested = False

    def request_cancel(self) -> None:
        self._cancel_requested = True

    def _raise_if_cancelled(self) -> None:
        if self._cancel_requested:
            raise UserCancelledError("Operation cancelled by user.")

    def _progress_hook(self, data: dict) -> None:
        self._raise_if_cancelled()

        status = data.get("status", "")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            downloaded = data.get("downloaded_bytes") or 0
            percent = (downloaded / total * 100.0) if total else 0.0
            speed = data.get("_speed_str") or "-"
            eta = data.get("_eta_str") or "-"
            self.progress_changed.emit(percent, speed, eta, "downloading")
        elif status == "finished":
            self.progress_changed.emit(100.0, "-", "0s", "download complete")

    def _build_output_template(self, temp_dir: Path, base_name: str) -> str:
        return str(temp_dir / f"{base_name}.%(ext)s")

    def _download_with_ytdlp(self, temp_dir: Path, base_name: str) -> Path:
        output_mode = self.options.output_mode

        if output_mode == "video_audio":
            format_selector = "bv*+ba/b"
        elif output_mode == "video_only":
            format_selector = "bv*[ext=mp4]/bv"
        else:
            format_selector = "bestaudio/best"

        ydl_opts = {
            "format": format_selector,
            "outtmpl": self._build_output_template(temp_dir, base_name),
            "restrictfilenames": False,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "progress_hooks": [self._progress_hook],
        }

        self.status_changed.emit("Downloading media...")
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(self.options.url, download=True)
            self._raise_if_cancelled()
            requested = ydl.prepare_filename(info)

        path = Path(requested)
        if not path.exists():
            stem_matches = list(temp_dir.glob(f"{base_name}.*"))
            media_files = [p for p in stem_matches if p.suffix.lower() not in {".part", ".ytdl"}]
            if not media_files:
                raise FileNotFoundError("Downloaded media file could not be located.")
            path = max(media_files, key=lambda p: p.stat().st_mtime)
        return path

    def _make_final_path(self, base_title: str, suffix: str) -> Path:
        clean = sanitize_filename(base_title)
        final = self.options.output_dir / f"{clean}{suffix}"
        return ensure_unique_path(final)

    def _trim_if_needed(self, source: Path, audio_only: bool) -> Path:
        self._raise_if_cancelled()
        if self.options.full_download:
            return source

        suffix = source.suffix or (".m4a" if audio_only else ".mp4")
        trimmed = ensure_unique_path(source.with_name(source.stem + "_trimmed" + suffix))
        trim_media(
            source,
            trimmed,
            self.options.start_seconds,
            self.options.end_seconds,
            audio_only=audio_only,
            callback=lambda s: self.status_changed.emit(s.capitalize() + "..."),
        )
        return trimmed

    @Slot()
    def run(self) -> None:
        temp_root_obj: Optional[tempfile.TemporaryDirectory] = None
        try:
            if not ffmpeg_exists():
                raise FFmpegError("ffmpeg and ffprobe must be installed and available in PATH.")

            self._raise_if_cancelled()
            self.options.output_dir.mkdir(parents=True, exist_ok=True)

            temp_root_obj = tempfile.TemporaryDirectory(prefix="yt_segment_dl_")
            temp_dir = Path(temp_root_obj.name)
            base_name = sanitize_filename(self.options.title_hint)

            downloaded_path = self._download_with_ytdlp(temp_dir, base_name)
            self._raise_if_cancelled()

            if self.options.output_mode == "audio_only":
                trimmed_source = self._trim_if_needed(downloaded_path, audio_only=True)
                final_path = self._make_final_path(base_name, f".{self.options.audio_format}")
                convert_audio(
                    trimmed_source,
                    final_path,
                    self.options.audio_format,
                    callback=lambda s: self.status_changed.emit(s.capitalize() + "..."),
                )
            else:
                final_source = self._trim_if_needed(downloaded_path, audio_only=False)
                ext = ".mp4" if self.options.output_mode in {"video_audio", "video_only"} else final_source.suffix
                final_path = self._make_final_path(base_name, ext)
                self.status_changed.emit("Finalizing file...")
                shutil.move(str(final_source), str(final_path))

            self.progress_changed.emit(100.0, "-", "0s", "done")
            self.finished.emit(str(final_path))
        except UserCancelledError as exc:
            self.cancelled.emit(str(exc))
        except (DownloadError, FFmpegError, FileNotFoundError, OSError, ValueError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:  # pragma: no cover
            self.failed.emit(f"Unexpected error: {exc}")
        finally:
            if temp_root_obj is not None:
                temp_root_obj.cleanup()
