from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

ProgressCallback = Callable[[str], None]


class FFmpegError(RuntimeError):
    pass


class CancelledError(RuntimeError):
    pass


def ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def run_ffmpeg(command: list[str]) -> None:
    process = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if process.returncode != 0:
        raise FFmpegError(process.stderr.strip() or "ffmpeg failed.")


def trim_media(
    input_file: Path,
    output_file: Path,
    start_seconds: Optional[int],
    end_seconds: Optional[int],
    audio_only: bool,
    callback: Optional[ProgressCallback] = None,
) -> None:
    if start_seconds is None and end_seconds is None:
        raise FFmpegError("Trim requested without a time range.")

    if callback:
        callback("trimming")

    command = ["ffmpeg", "-y"]
    if start_seconds is not None:
        command += ["-ss", str(start_seconds)]
    command += ["-i", str(input_file)]
    if end_seconds is not None:
        if start_seconds is not None:
            duration = max(0, end_seconds - start_seconds)
            command += ["-t", str(duration)]
        else:
            command += ["-to", str(end_seconds)]

    if audio_only:
        command += ["-vn", "-acodec", "copy", str(output_file)]
    else:
        command += ["-c", "copy", str(output_file)]

    run_ffmpeg(command)


def convert_audio(
    input_file: Path,
    output_file: Path,
    audio_format: str,
    callback: Optional[ProgressCallback] = None,
) -> None:
    if callback:
        callback("processing audio")

    command = ["ffmpeg", "-y", "-i", str(input_file)]
    if audio_format == "mp3":
        command += ["-vn", "-codec:a", "libmp3lame", "-q:a", "2", str(output_file)]
    elif audio_format == "m4a":
        command += ["-vn", "-codec:a", "aac", "-b:a", "192k", str(output_file)]
    else:
        raise FFmpegError(f"Unsupported audio format: {audio_format}")

    run_ffmpeg(command)
