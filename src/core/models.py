from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True)
class VideoInfo:
    url: str
    title: str
    duration: int
    thumbnail_url: str
    uploader: str
    resolution_text: str
    webpage_url: str


@dataclass(slots=True)
class DownloadOptions:
    url: str
    output_dir: Path
    output_mode: str  # video_audio | video_only | audio_only
    audio_format: str  # mp3 | m4a
    start_seconds: Optional[int]
    end_seconds: Optional[int]
    full_download: bool
    title_hint: str
