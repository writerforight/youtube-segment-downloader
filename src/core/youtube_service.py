from __future__ import annotations

from typing import Callable, Optional

from yt_dlp import YoutubeDL

from .models import VideoInfo

MetadataCallback = Callable[[dict], None]


class YouTubeService:
    @staticmethod
    def fetch_info(url: str) -> VideoInfo:
        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        with YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)

        duration = int(info.get("duration") or 0)
        title = info.get("title") or "Untitled"
        thumbnail = info.get("thumbnail") or ""
        uploader = info.get("uploader") or "Unknown uploader"

        formats = info.get("formats") or []
        max_height = 0
        for fmt in formats:
            height = fmt.get("height") or 0
            if isinstance(height, int):
                max_height = max(max_height, height)
        resolution_text = f"Up to {max_height}p" if max_height else "Unknown"

        return VideoInfo(
            url=url,
            title=title,
            duration=duration,
            thumbnail_url=thumbnail,
            uploader=uploader,
            resolution_text=resolution_text,
            webpage_url=info.get("webpage_url") or url,
        )
