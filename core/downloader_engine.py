import logging
import os
import re
import sys
import yt_dlp

log = logging.getLogger("downloader")

# Ensure Deno is on PATH so yt-dlp can use it as a JS runtime
_deno_path = os.path.join(os.environ.get("USERPROFILE", ""), ".deno", "bin")
if _deno_path and os.path.isdir(_deno_path) and _deno_path not in os.environ.get("PATH", ""):
    os.environ["PATH"] = os.environ.get("PATH", "") + os.pathsep + _deno_path

# Use yt-dlp's native curl_cffi backend when available (TLS fingerprint
# impersonation, useful for Vimeo / Dailymotion / sites that block default
# urllib). Set to the string "curl_cffi" so yt-dlp drives the adapter itself.
try:
    import curl_cffi  # noqa: F401
    CURL_CFFI_AVAILABLE = True
except Exception as _curl_cffi_err:
    CURL_CFFI_AVAILABLE = False
    # Silently falling back here used to hide the real cause of 403s on
    # Instagram/Dailymotion/etc (they block plain urllib via TLS fingerprint
    # checks). Log it loudly so it shows up in app.log instead of looking
    # like an unexplained 403.
    log.warning(
        "curl_cffi not available (%s) - falling back to urllib. Sites that "
        "require browser TLS fingerprinting (Instagram, Dailymotion, etc.) "
        "are likely to return 403 until `pip install curl-cffi` succeeds "
        "in this environment.", _curl_cffi_err,
    )

# yt-dlp itself reports its running version; log it once at import time so a
# stale bundled/venv copy is obvious in app.log rather than a mystery 403.
log.info("Using yt-dlp version %s", getattr(yt_dlp.version, "__version__", "unknown"))
if getattr(yt_dlp.version, "__version__", "0") < "2026.08.19":
    log.warning(
        "yt-dlp version is older than 2026.08.19, which fixed a YouTube "
        "`android_vr` client bug that caused '403 Forbidden' on every "
        "download. Run `pip install -U yt-dlp` (or update however this "
        "app's dependencies were installed)."
    )


BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
FFMPEG_BIN_PATH = os.path.join(BASE_DIR, "bin")

_FORBIDDEN_HINT = (
    " YouTube is blocking this IP. Fixes: (1) add login cookies in Settings, "
    "(2) set a proxy, (3) switch networks (restart router / mobile hotspot)."
)
_FORBIDDEN_RE = re.compile(r"(403|forbidden|unavailable for legal reasons|geo.restricted)", re.IGNORECASE)


def annotate_error(err):
    """Return the error string, appending a fix hint when it looks like an IP-level 403 block."""
    msg = str(err)
    if _FORBIDDEN_RE.search(msg):
        return msg.rstrip(" .") + _FORBIDDEN_HINT
    return msg


class DownloaderEngine:
    def __init__(self, ffmpeg_path=None, output_dir="downloads", proxy="", cookiefile="", cookies_from_browser=""):
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path else FFMPEG_BIN_PATH
        self.output_dir = output_dir
        self.proxy = proxy or ""
        self.cookiefile = cookiefile or ""
        self.cookies_from_browser = cookies_from_browser or ""

    def update_config(self, output_dir=None, proxy=None, cookiefile=None, cookies_from_browser=None):
        if output_dir is not None:
            self.output_dir = output_dir
        if proxy is not None:
            self.proxy = proxy
        if cookiefile is not None:
            self.cookiefile = cookiefile
        if cookies_from_browser is not None:
            self.cookies_from_browser = cookies_from_browser

    def _base_opts(self, quiet=False):
        opts = {
            "ffmpeg_location": self.ffmpeg_path,
            "remote_components": {"ejs:github"},
            "user_agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
            ),
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        }
        if quiet:
            opts.update({"quiet": True, "no_warnings": True, "skip_download": True})
        if CURL_CFFI_AVAILABLE:
            opts["http_client"] = "curl_cffi"
        if self.proxy:
            opts["proxy"] = self.proxy
        # An explicitly chosen cookies.txt file wins if set. Otherwise, if the
        # user picked a browser, read cookies live from that browser's own
        # cookie store on every run - this is what lets Instagram/etc logins
        # keep working automatically without the user re-exporting a file
        # every time the session rotates.
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile
        elif self.cookies_from_browser:
            opts["cookiesfrombrowser"] = (self.cookies_from_browser, None, None, None)
        return opts

    def get_download_options(self, quality, progress_hook=None, format_id=None):
        opts = {
            "progress_hooks": [progress_hook] if progress_hook else [],
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
        }
        opts.update(self._base_opts())

        if format_id:
            opts["format"] = format_id
        elif quality == "Audio":
            opts.update({
                "format": "bestaudio/best",
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }],
            })
        elif quality == "1080p":
            opts.update({
                "format": "bestvideo[height<=?1080]+bestaudio/best[height<=?1080]/best",
                "merge_output_format": "mp4",
            })
        elif quality == "1440p":
            opts.update({
                "format": "bestvideo[height<=?1440]+bestaudio/best[height<=?1440]/best",
                "merge_output_format": "mp4",
            })
        elif quality == "2160p":
            opts.update({
                "format": "bestvideo[height<=?2160]+bestaudio/best[height<=?2160]/best",
                "merge_output_format": "mp4",
            })
        else:
            opts.update({
                "format": "bestvideo[height<=?720]+bestaudio/best[height<=?720]/best",
                "merge_output_format": "mp4",
            })

        return opts

    def fetch_metadata(self, url):
        opts = self._base_opts(quiet=True)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", "Unknown"),
                "uploader": info.get("uploader") or info.get("channel", "Unknown"),
                "duration": info.get("duration_string") or self._format_duration(info.get("duration")),
                "thumbnail": info.get("thumbnail", None),
                "website": info.get("extractor", "?"),
                "view_count": info.get("view_count"),
            }

    def fetch_formats(self, url):
        opts = self._base_opts(quiet=True)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            for f in info.get("formats", []):
                if f.get("vcodec") != "none" or f.get("acodec") != "none":
                    size = f.get("filesize") or f.get("filesize_approx")
                    formats.append({
                        "id": f.get("format_id"),
                        "ext": f.get("ext", "?"),
                        "res": f.get("resolution") or f"{f.get('height', '?')}p",
                        "fps": f.get("fps", "?"),
                        "vcodec": (f.get("vcodec") or "none")[:24],
                        "acodec": (f.get("acodec") or "none")[:16],
                        "size_mb": round(size / 1e6, 1) if size else None,
                        "tbr": f.get("tbr"),
                    })
            return formats

    def download(self, url, quality, progress_hook=None, format_id=None):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
        options = self.get_download_options(quality, progress_hook=progress_hook, format_id=format_id)
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
            ydl.download([url])
            return info

    @staticmethod
    def _format_duration(seconds):
        if not seconds:
            return "?"
        h, rem = divmod(int(seconds), 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
