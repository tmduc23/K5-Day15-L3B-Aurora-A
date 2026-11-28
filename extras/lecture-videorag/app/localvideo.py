"""LMS lecture videos: uploaded files and direct download links (no YouTube, usually no subtitles).

The file is stored under settings.uploads_dir and kept: it is the source for Whisper, for keyframes,
and for in-app playback (citations point to /media/videos/<file>#t=<seconds>).
"""
from __future__ import annotations

import re
import secrets
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import cv2

VIDEO_EXTS = {".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi"}
CONTENT_TYPE_EXT = {
    "video/mp4": ".mp4", "video/x-m4v": ".m4v", "video/quicktime": ".mov", "video/webm": ".webm",
    "video/x-matroska": ".mkv", "video/x-msvideo": ".avi",
}
CHUNK = 1 << 20


class InvalidVideoSource(ValueError):
    """The file or link cannot be used as a lecture video (message is shown to the user)."""


@dataclass
class LocalSource:
    key: str                       # "f" + 12 hex: frames folder and unique id inside the series
    title: str
    media_path: str | None = None  # relative to uploads_dir, set once the file is on disk
    source_url: str | None = None  # direct link, downloaded by the worker
    duration: float | None = None


def new_key() -> str:
    return "f" + secrets.token_hex(6)


def check_extension(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext not in VIDEO_EXTS:
        raise InvalidVideoSource(
            f"'{filename}': chỉ nhận file video {', '.join(sorted(VIDEO_EXTS))}")
    return ext


def title_from_filename(filename: str) -> str:
    stem = Path(filename or "video").stem
    return re.sub(r"[_]+", " ", stem).strip() or "Video"


def natural_key(name: str) -> list:
    """'Bai 2' sorts before 'Bai 10' (lecture files are usually numbered without zero padding)."""
    return [int(p) if p.isdigit() else p.lower() for p in re.split(r"(\d+)", name or "")]


def check_direct_url(url: str) -> str:
    url = (url or "").strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise InvalidVideoSource(f"Link không hợp lệ (cần http/https): {url[:200]}")
    return url


def title_from_url(url: str) -> str:
    name = urllib.parse.unquote(Path(urllib.parse.urlsplit(url).path).name)
    return title_from_filename(name) if name else urllib.parse.urlsplit(url).netloc


def save_stream(src: BinaryIO, dest: Path, max_bytes: int) -> int:
    """Copy src to dest in chunks; refuse (and remove the partial file) past max_bytes."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    try:
        with open(dest, "wb") as out:
            while True:
                buf = src.read(CHUNK)
                if not buf:
                    break
                total += len(buf)
                if total > max_bytes:
                    raise InvalidVideoSource(f"File lớn hơn giới hạn {max_bytes // (1 << 20)} MB")
                out.write(buf)
    except BaseException:
        dest.unlink(missing_ok=True)
        raise
    if total == 0:
        dest.unlink(missing_ok=True)
        raise InvalidVideoSource("File rỗng")
    return total


def download_url(url: str, out_dir: Path, key: str, max_bytes: int, timeout: float = 60.0) -> Path:
    """Download a direct video link. LMS pages that need a login return HTML: refuse those clearly."""
    req = urllib.request.Request(check_direct_url(url), headers={"User-Agent": "Mozilla/5.0 lecture-videorag"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype.startswith("text/") or ctype in ("application/json", "application/xhtml+xml"):
            raise InvalidVideoSource(
                "Link trả về trang web chứ không phải file video (LMS thường bắt đăng nhập). "
                "Hãy tải video về máy rồi dùng nút tải file lên.")
        length = resp.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > max_bytes:
            raise InvalidVideoSource(f"File lớn hơn giới hạn {max_bytes // (1 << 20)} MB")
        ext = Path(urllib.parse.urlsplit(resp.geturl() if hasattr(resp, "geturl") else url).path).suffix.lower()
        if ext not in VIDEO_EXTS:
            ext = CONTENT_TYPE_EXT.get(ctype, ".mp4")
        dest = out_dir / f"{key}{ext}"
        save_stream(resp, dest, max_bytes)
    return dest


def probe(path: Path) -> float | None:
    """Duration in seconds; raises if OpenCV cannot read a single frame (not a video / unsupported codec)."""
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened() or not cap.grab():
            raise InvalidVideoSource("Không đọc được hình ảnh trong file (không phải video hoặc codec không hỗ trợ)")
        fps = cap.get(cv2.CAP_PROP_FPS) or 0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        return round(frames / fps, 1) if fps > 0 and frames > 0 else None
    finally:
        cap.release()


def has_audio(path: Path) -> bool:
    """True if the file has an audio track (Whisper needs one). Unknown (no PyAV) counts as True."""
    try:
        import av
    except ImportError:
        return True
    try:
        with av.open(str(path)) as c:
            return len(c.streams.audio) > 0
    except Exception:
        return False


def remove_file(uploads_dir: Path, media_path: str | None) -> None:
    if not media_path:
        return
    p = (uploads_dir / media_path).resolve()
    if p.is_relative_to(uploads_dir.resolve()):
        p.unlink(missing_ok=True)

