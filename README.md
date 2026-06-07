# 🎬 Video Downloader

A clean, open-source desktop application to download videos and audio from **1800+ websites** — YouTube, Vimeo, Dailymotion, TikTok, SoundCloud, Rumble, and more.

No ads. No malware. No subscriptions. Just paste a URL and download.

Powered by **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** under the hood, wrapped in a smooth **Flet** desktop GUI with browser TLS impersonation (curl_cffi) for sites that block standard requests.

---

## ⚡ Features

- **1800+ sites supported** — YouTube, Vimeo, Dailymotion, TikTok, Rumble, Odysee, SoundCloud, Twitch VODs, X (Twitter), Instagram, Facebook, and more
- **Quality selection** — Choose 2160p, 1440p, 1080p, 720p, or extract audio as MP3
- **Browser impersonation** — Automatically uses TLS fingerprinting to bypass Vimeo, Dailymotion, and other platform blocks
- **Download queue** — Queue multiple downloads and watch real-time progress
- **Download history** — Tracks all past downloads with one-click retry
- **Settings panel** — Configurable output folder, default quality, proxy, cookies for logged-in content
- **Dark/Light theme** toggle
- **Keyboard shortcuts** — `Ctrl+H` History, `Ctrl+S` Settings, `Enter` add to queue

---

## 📋 Requirements

| Item | Details |
|---|---|
| **Python** | 3.9+ |
| **FFmpeg** | Required for video merging and audio extraction (see install below) |

---

## 🚀 Quick Start

### 1. Install FFmpeg

Download the latest build from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and extract it to `bin/` in this folder:

```
file_downloader/
└── bin/
    ├── ffmpeg.exe
    ├── ffplay.exe
    └── ffprobe.exe
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run

```bash
python main.py
```

---

## 📂 Project Structure

```
file_downloader/
├── bin/                        # FFmpeg binaries (download separately)
│   ├── ffmpeg.exe
│   ├── ffplay.exe
│   └── ffprobe.exe
├── core/                       # Business logic
│   ├── __init__.py
│   ├── downloader_engine.py    # yt-dlp wrapper with curl_cffi impersonation
│   ├── queue_manager.py        # Download queue with concurrent workers
│   ├── settings_manager.py     # Persistent settings (JSON)
│   └── history_manager.py      # Download history tracking
├── ui/                         # Flet desktop UI
│   ├── __init__.py
│   ├── components.py           # Shared UI components (status chips, nav bar)
│   ├── main_view.py            # Main download screen with queue
│   ├── history_view.py         # Past downloads table
│   ├── settings_view.py        # Settings panel
│   └── native_dialogs.py       # Windows file/folder pickers
├── main.py                     # App entry point
├── requirements.txt            # Python dependencies
├── README.md                   # This file
├── .gitignore                  # Git ignore rules
└── LICENSE                     # MIT License
```

---

## 🎯 Usage

1. **Paste a URL** from any supported platform
2. **Select quality** — 2160p, 1440p, 1080p, 720p, or Audio
3. **Click "Add to Queue"** — download starts immediately with real-time progress
4. **Check your downloads folder** — files saved as `<title>.<ext>`

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Enter` | Add URL to queue |
| `Ctrl + H` | Open history |
| `Ctrl + S` | Open settings |

---

## 🔧 Troubleshooting

### "Connection aborted" or "Unable to download JSON metadata"

The app uses **curl_cffi** browser impersonation to bypass platform blocks. If some sites still fail:

1. Update yt-dlp: click **"Update yt-dlp"** in Settings
2. Ensure curl_cffi is installed: `pip install curl-cffi`
3. Some platforms (like Vimeo) may block your ISP/network entirely — try a different network

### Audio extraction fails (MP3)

Ensure your FFmpeg binaries in `bin/` are working:
```bash
bin\ffmpeg.exe -version
```

### Where do downloaded files go?

By default, files are saved in the `downloads/` folder inside the project directory. Change this in **Settings > Downloads Folder**.

---

## 📜 Supported Platforms (Top Picks)

| Platform | Status | Notes |
|---|---|---|
| YouTube | ✅ Full support | Videos, Shorts, Music |
| Vimeo | ✅ Via impersonation | TLS fingerprint required |
| Dailymotion | ✅ Via impersonation | TLS fingerprint required |
| TikTok | ✅ Video download | Reels and regular videos |
| SoundCloud | ✅ Audio extraction | MP3 output |
| Rumble | ✅ Public videos | Some geo-restricted content may fail |
| Twitch VODs | ✅ Past broadcasts | Videos and clips |
| X (Twitter) | ✅ Video tweets | May require cookies for some accounts |
| Instagram | ⚠️ Selective | Public accounts only, may need cookies |
| Facebook | ⚠️ Selective | Public videos only, may need cookies |

---

## 🛠️ Built With

| Technology | Purpose |
|---|---|
| **[Flet](https://flet.dev/)** | Desktop GUI framework (Flutter-based Python) |
| **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** | Download engine (1800+ site support) |
| **[curl_cffi](https://github.com/lexiforest/curl_cffi)** | TLS fingerprinting for browser impersonation |
| **FFmpeg** | Video merging & audio codec support |

---

## 📝 License

MIT License — see [LICENSE](LICENSE) file.

---

*Built for people who want to save media without ads, malware, or sign-ups.*
#   V i d e o D o w n l o a d e r 
 
 
