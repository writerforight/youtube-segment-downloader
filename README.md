# YouTube Segment Downloader

Modern PySide6 desktop application for downloading either a full YouTube video or only a selected time range.

## Features

- Modern dark desktop UI
- Fetch video title, duration, uploader, resolution and thumbnail
- Dual-handle trim slider
- Time entry fields synchronized with the slider
- Download modes:
  - Video + audio
  - Video only
  - Audio only
- Audio output options: MP3 or M4A
- Output folder picker
- Progress bar, percentage, speed, ETA and status text
- Background worker thread so the GUI stays responsive
- Cancel support
- ffmpeg validation
- Safe filename sanitization and duplicate filename handling

## Project Structure

```text
youtube_segment_downloader/
├── main.py
├── requirements.txt
├── README.md
└── src/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   ├── download_worker.py
    │   ├── ffmpeg_utils.py
    │   ├── models.py
    │   ├── utils.py
    │   └── youtube_service.py
    └── ui/
        ├── __init__.py
        ├── main_window.py
        └── range_slider.py
```

## Installation

### 1) Create and activate a virtual environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows CMD

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

## 2) Install Python dependencies

```bash
pip install -r requirements.txt
```

## 3) Install ffmpeg

Install ffmpeg and make sure both `ffmpeg` and `ffprobe` are available in PATH.

You can verify with:

```bash
ffmpeg -version
ffprobe -version
```

## Run

```bash
python main.py
```

## Build EXE with PyInstaller

Install PyInstaller:

```bash
pip install pyinstaller
```

Then build:

```bash
pyinstaller --noconfirm --windowed --name "YouTube Segment Downloader" --collect-all PySide6 --hidden-import=PySide6.QtCore --hidden-import=PySide6.QtGui --hidden-import=PySide6.QtWidgets main.py
```

## Notes

- The app uses `yt-dlp` for metadata and downloads.
- The app uses `ffmpeg` for exact trimming and audio conversion.
- For `audio only`, the app downloads best available audio, optionally trims it, then converts it to the selected audio format.
- For `video only`, the app downloads the best video stream available.
- For `video + audio`, yt-dlp merges streams and the app can trim the merged output.
