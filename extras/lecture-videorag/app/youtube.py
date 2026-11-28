"""YouTube access: URL validation, playlist expansion, metadata, subtitles, media download.

Only public data the platform serves is used. Private, members-only or DRM content is not bypassed.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)

ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
PLAYLIST_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,64}$")


class InvalidYouTubeUrl(ValueError):
    pass


class TranscriptUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ParsedUrl:
    kind: str  # "video" | "playlist"
    id: str


def parse_youtube_url(url: str) -> ParsedUrl:
    """Validate a YouTube URL and return what it points at.

    A watch URL that also carries a playlist (`watch?v=X&list=Y`) is treated as the playlist,
    since the input of this app is a lecture series.
    """
    raw = (url or "").strip()
    if not raw:
        raise InvalidYouTubeUrl("URL trống")
    if VIDEO_ID_RE.match(raw):
        return ParsedUrl("video", raw)
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in ("http", "https") or host not in ALLOWED_HOSTS:
        raise InvalidYouTubeUrl(f"Không phải link YouTube: {url}")
    qs = parse_qs(parsed.query)
    playlist = (qs.get("list") or [None])[0]
    if playlist and PLAYLIST_ID_RE.match(playlist) and not playlist.startswith("RD"):  # RD* = auto mixes
        return ParsedUrl("playlist", playlist)
    if host.endswith("youtu.be"):
        vid = parsed.path.lstrip("/").split("/")[0]
    elif parsed.path == "/watch":
        vid = (qs.get("v") or [""])[0]
    else:
        m = re.match(r"^/(?:embed|shorts|live|v)/([^/?#]+)", parsed.path)
        vid = m.group(1) if m else ""
    if not VIDEO_ID_RE.match(vid):
        raise InvalidYouTubeUrl(f"Không tìm thấy mã video hợp lệ trong: {url}")
    return ParsedUrl("video", vid)


@dataclass
class VideoInfo:
    youtube_id: str
    title: str | None = None
    channel: str | None = None
    duration: float | None = None
    thumbnail_url: str | None = None


def _ydl(opts: dict | None = None):
    import yt_dlp

    base = {"quiet": True, "no_warnings": True, "noprogress": True, "skip_download": True}
    base.update(opts or {})
    return yt_dlp.YoutubeDL(base)


def expand(url: str) -> tuple[str | None, list[VideoInfo]]:
    """Resolve a URL into (series title, ordered list of videos)."""
    p = parse_youtube_url(url)
    if p.kind == "video":
        return None, [VideoInfo(youtube_id=p.id)]
    with _ydl({"extract_flat": "in_playlist"}) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/playlist?list={p.id}", download=False)
    videos = []
    for e in info.get("entries") or []:
        vid = e.get("id")
        if not vid or not VIDEO_ID_RE.match(vid):
            continue
        thumbs = e.get("thumbnails") or []
        videos.append(VideoInfo(
            youtube_id=vid,
            title=e.get("title"),
            channel=e.get("channel") or e.get("uploader"),
            duration=e.get("duration"),
            thumbnail_url=thumbs[-1]["url"] if thumbs else None,
        ))
    return info.get("title"), videos


def fetch_metadata(video_id: str) -> VideoInfo:
    with _ydl() as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return VideoInfo(
        youtube_id=video_id,
        title=info.get("title"),
        channel=info.get("channel") or info.get("uploader"),
        duration=info.get("duration"),
        thumbnail_url=info.get("thumbnail"),
    )


@dataclass
class Segment:
    start: float
    end: float
    text: str


def fetch_subtitles(video_id: str, languages: list[str]) -> tuple[list[Segment], str, str]:
    """Return (segments, language_code, source). Prefers manual subtitles in the given languages,
    then auto-generated ones, then any available track."""
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api import CouldNotRetrieveTranscript

    api = YouTubeTranscriptApi()
    try:
        tlist = api.list(video_id)
        transcript = None
        for finder in (tlist.find_manually_created_transcript, tlist.find_generated_transcript):
            try:
                transcript = finder(languages)
                break
            except CouldNotRetrieveTranscript:
                continue
        if transcript is None:
            available = list(tlist)
            if not available:
                raise TranscriptUnavailable("Video không có phụ đề")
            transcript = available[0]
        fetched = transcript.fetch()
    except CouldNotRetrieveTranscript as e:
        raise TranscriptUnavailable(f"Không lấy được phụ đề: {type(e).__name__}") from e
    segments = [
        Segment(start=float(s.start), end=float(s.start) + float(s.duration), text=s.text)
        for s in fetched.snippets
        if s.text and s.text.strip()
    ]
    if not segments:
        raise TranscriptUnavailable("Phụ đề rỗng")
    source = "youtube-auto" if transcript.is_generated else "youtube-manual"
    return segments, transcript.language_code, source


def download_video(video_id: str, out_dir: Path, max_height: int) -> Path:
    """Download a single video-only stream (no audio, no merge => no ffmpeg needed).

    H.264 is preferred because OpenCV decodes it everywhere.
    """
    h = int(max_height)
    fmt = (
        f"bv*[height<={h}][vcodec^=avc1]/bv*[height<={h}][ext=mp4]/"
        f"b[height<={h}][ext=mp4]/bv*[height<={h}]/18"
    )
    return _download(video_id, out_dir, fmt, "video")


def download_audio(video_id: str, out_dir: Path) -> Path:
    return _download(video_id, out_dir, "bestaudio[ext=m4a]/bestaudio", "audio")


def _download(video_id: str, out_dir: Path, fmt: str, tag: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        "format": fmt,
        "skip_download": False,
        "noplaylist": True,
        "outtmpl": str(out_dir / f"{video_id}.{tag}.%(ext)s"),
        "overwrites": True,
    }
    with _ydl(opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
        path = Path(ydl.prepare_filename(info))
    if not path.exists():
        raise RuntimeError(f"Tải {tag} thất bại cho {video_id}")
    return path


def watch_url(video_id: str, seconds: float | None = None) -> str:
    if seconds is None:
        return f"https://www.youtube.com/watch?v={video_id}"
    return f"https://youtu.be/{video_id}?t={int(seconds)}"
