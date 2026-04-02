from __future__ import annotations

import re
from pathlib import Path

INVALID_FILENAME_CHARS = r'[<>:"/\\|?*\x00-\x1F]'


def sanitize_filename(name: str, replacement: str = "_") -> str:
    """Sanitize a filename for Windows compatibility."""
    cleaned = re.sub(INVALID_FILENAME_CHARS, replacement, name).strip(" .")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "download"


def ensure_unique_path(path: Path) -> Path:
    """Return a unique path by appending a numeric suffix if needed."""
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    parent = path.parent
    counter = 1
    while True:
        candidate = parent / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def format_seconds(seconds: int | float | None) -> str:
    if seconds is None:
        return "00:00"
    total = max(0, int(round(seconds)))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def parse_time_to_seconds(value: str) -> int:
    text = value.strip()
    if not text:
        raise ValueError("Time field cannot be empty.")

    if text.isdigit():
        return int(text)

    parts = text.split(":")
    if not 1 <= len(parts) <= 3:
        raise ValueError("Invalid time format. Use SS, MM:SS, or HH:MM:SS.")

    try:
        nums = [int(p) for p in parts]
    except ValueError as exc:
        raise ValueError("Time must contain only digits and colons.") from exc

    if len(nums) == 3:
        h, m, s = nums
    elif len(nums) == 2:
        h, m, s = 0, nums[0], nums[1]
    else:
        h, m, s = 0, 0, nums[0]

    if m < 0 or s < 0 or h < 0 or m >= 60 or s >= 60:
        raise ValueError("Invalid time values.")

    return h * 3600 + m * 60 + s
