# YouTube Segment Downloader

**YouTube Segment Downloader is a desktop app (Python, PySide6) for downloading either a whole YouTube
video or only a chosen time range of it — as video with audio, video only, or audio only (MP3 or
M4A).** You paste a link, see the video's details, set the start and end with a two-handle slider, and
download just that part. It uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to fetch the video and
[ffmpeg](https://ffmpeg.org) for exact trimming and audio conversion. It was built by
[Eren Can Almaz](https://writerforight.github.io), an Electrical Engineering student at RWTH Aachen
University.

## Features

- Fetches the title, duration, uploader, resolution and thumbnail of a video.
- **Trim before saving**: a dual-handle range slider, synchronized with start/end time fields, and the
  length of the selection.
- Download modes: **video + audio**, **video only**, **audio only** (MP3 or M4A).
- Progress bar with percentage, speed, ETA and status; downloads run in a background thread, so the
  window stays responsive, and can be cancelled.
- Checks that ffmpeg is installed, makes file names safe and never overwrites an existing file.
- Dark interface; output folder picker.

## How it works

1. `yt-dlp` reads the video metadata (`src/core/youtube_service.py`).
2. A worker thread downloads the best matching stream(s) into a temporary folder
   (`src/core/download_worker.py`); for *video + audio* yt-dlp merges the streams.
3. If a time range is selected, `ffmpeg` cuts exactly that range; for *audio only* it then converts the
   result to MP3 or M4A (`src/core/ffmpeg_utils.py`).
4. The file is moved to the chosen folder under a sanitized, non-conflicting name.

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) with `ffmpeg` and `ffprobe` on your `PATH`
  (check with `ffmpeg -version`)
- Python packages: `PySide6`, `yt-dlp` (see `requirements.txt`)

## Install and run

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1     Windows CMD: .venv\Scripts\activate.bat
# macOS / Linux:      source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Keep `yt-dlp` up to date (`pip install -U yt-dlp`); YouTube changes often and old versions stop working.

## Build a Windows executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "YouTube Segment Downloader" --collect-all PySide6 \
  --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets main.py
```

## Project structure

```text
main.py                     entry point
src/core/youtube_service.py metadata via yt-dlp
src/core/download_worker.py background download + trimming
src/core/ffmpeg_utils.py    ffmpeg checks, trimming, audio conversion
src/core/models.py          download options
src/core/utils.py           time formatting, safe file names
src/ui/main_window.py       the window
src/ui/range_slider.py      two-handle range slider widget
```

## Responsible use

Only download videos you have the right to download, and respect YouTube's Terms of Service and the
creators' copyright.

## Author

**Eren Can Almaz** — Electrical Engineering (Elektrotechnik) student at RWTH Aachen University.
GitHub [@writerforight](https://github.com/writerforight) · website
[writerforight.github.io](https://writerforight.github.io). Other projects:
[Neural Space Deformation](https://github.com/writerforight/mlp-space-deformation) ·
[Ders Transkript](https://github.com/writerforight/ders-transkript).

## License

MIT — see [LICENSE](LICENSE).
