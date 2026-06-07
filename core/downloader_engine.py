import os
import sys
import yt_dlp

# Try to enable curl-cffi as the HTTP backend if available
try:
    from curl_cffi import requests as cc_requests
    # Monkey-patch yt-dlp's default backend to use curl_cffi
    _orig_init = yt_dlp.networking._adapter.Registry.__init__

    def _new_init(self):
        _orig_init(self)
        # Register curl_cffi adapter if not already registered
        from yt_dlp.networking.curl import CurlAdapter
        from yt_dlp.networking.helper import AdapterName
        self.register_adapter('curl', CurlAdapter)
    
    yt_dlp.networking._adapter.Registry.__init__ = _new_init
    CURL_CFFI_AVAILABLE = True
except Exception:
    CURL_CFFI_AVAILABLE = False


BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
FFMPEG_BIN_PATH = os.path.join(BASE_DIR, "bin")


class DownloaderEngine:
    def __init__(self, ffmpeg_path=None, output_dir="downloads", proxy="", cookiefile=""):
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path else FFMPEG_BIN_PATH
        self.output_dir = output_dir
        self.proxy = proxy or ""
        self.cookiefile = cookiefile or ""

    def update_config(self, output_dir=None, proxy=None, cookiefile=None):
        if output_dir is not None:
            self.output_dir = output_dir
        if proxy is not None:
            self.proxy = proxy
        if cookiefile is not None:
            self.cookiefile = cookiefile

    def get_download_options(self, quality, progress_hook=None, format_id=None):
        opts = {
            "progress_hooks": [progress_hook] if progress_hook else [],
            "ffmpeg_location": self.ffmpeg_path,
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
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

        if CURL_CFFI_AVAILABLE:
            opts["http_client"] = _create_curl_http_client()

        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile

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
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "merge_output_format": "mp4",
            })
        elif quality == "1440p":
            opts.update({
                "format": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "merge_output_format": "mp4",
            })
        elif quality == "2160p":
            opts.update({
                "format": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "merge_output_format": "mp4",
            })
        else:
            opts.update({
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "merge_output_format": "mp4",
            })

        return opts


def _create_curl_http_client():
    """Create an HTTP client for yt-dlp that uses curl_cffi under the hood.
    
    This is a workaround to enable TLS fingerprint impersonation with Vimeo,
    Dailymotion, and other platforms that block default urllib3 requests.
    """
    from curl_cffi import BrowserType
    
    # Try Chrome 125 or fallback to closest available
    TARGETS = ['chrome124', 'chrome123', 'chrome120', 'chrome119']
    target = None
    for t in TARGETS:
        try:
            _check_browser_type(t)
            target = t
            break
        except Exception:
            continue
    
    if target is None:
        # List all available Chrome targets to help debug
        all_chrome = [bt.value for bt in BrowserType if 'chrome' in str(bt).lower()]
        raise RuntimeError(
            f"No Chrome impersonation target found. Available: {all_chrome}"
        )
    
    def http_client_func(url, headers, **kwargs):
        import yt_dlp.utils
        
        # Use curl_cffi to make the request with full TLS fingerprinting
        resp = cc_requests.get(
            str(url),
            headers=headers,
            impersonate=target,
            allow_redirects=True,
            timeout=30,
        )
        
        # Wrap in yt-dlp compatible response object
        from yt_dlp.utils import write_string
        
        # Build a response that looks like requests.Response to yt-dlp's networking layer
        class _CurlResponse:
            def __init__(self, resp):
                self._resp = resp
            
            @property
            def url(self):
                return str(self._resp.url)
            
            @property
            def status_code(self):
                return self._resp.status_code
            
            @property
            def headers(self):
                return yt_dlp.utils.canned_headers()  # fallback
            
            def raise_for_status(self):
                if not 200 <= self.status_code < 400:
                    from yt_dlp.utils import extractarser_error
                    raise yt_dlp.utils.DownloadError(
                        f"HTTP Error {self.status_code}: {self._resp.reason}", 
                        self.status_code
                    )
            
            def read(self):
                return self._resp.content
            
            def iter_content(self, chunk_size=None):
                yield self._resp.content
            
            def text(self):
                return self._resp.text
        
        return _CurlResponse(resp)
    
    return http_client_func


def _check_browser_type(name):
    from curl_cffi import BrowserType
    for bt in BrowserType:
        if bt.value == name:
            return True
    raise KeyError(f"BrowserType {name} not found")


class DownloaderEngine:
    def __init__(self, ffmpeg_path=None, output_dir="downloads", proxy="", cookiefile=""):
        self.ffmpeg_path = ffmpeg_path if ffmpeg_path else FFMPEG_BIN_PATH
        self.output_dir = output_dir
        self.proxy = proxy or ""
        self.cookiefile = cookiefile or ""

    def update_config(self, output_dir=None, proxy=None, cookiefile=None):
        if output_dir is not None:
            self.output_dir = output_dir
        if proxy is not None:
            self.proxy = proxy
        if cookiefile is not None:
            self.cookiefile = cookiefile

    def get_download_options(self, quality, progress_hook=None, format_id=None):
        opts = {
            "progress_hooks": [progress_hook] if progress_hook else [],
            "ffmpeg_location": self.ffmpeg_path,
            "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
            "noplaylist": True,
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

        if CURL_CFFI_AVAILABLE:
            opts["http_client"] = _create_curl_http_client()

        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile

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
                "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "merge_output_format": "mp4",
            })
        elif quality == "1440p":
            opts.update({
                "format": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
                "merge_output_format": "mp4",
            })
        elif quality == "2160p":
            opts.update({
                "format": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
                "merge_output_format": "mp4",
            })
        else:
            opts.update({
                "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "merge_output_format": "mp4",
            })

        return opts

    def fetch_metadata(self, url):
        opts = {
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "ffmpeg_location": self.ffmpeg_path,
        }
        if CURL_CFFI_AVAILABLE:
            opts["http_client"] = _create_curl_http_client()
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile
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
        opts = {
            "quiet": True,
            "skip_download": True,
            "ffmpeg_location": self.ffmpeg_path,
        }
        if CURL_CFFI_AVAILABLE:
            opts["http_client"] = _create_curl_http_client()
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookiefile and os.path.exists(self.cookiefile):
            opts["cookiefile"] = self.cookiefile
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
