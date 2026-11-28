"""Transcript cleanup, chunking with timestamps, and the Whisper fallback."""
from __future__ import annotations

import html
import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .youtube import Segment, TranscriptUnavailable

log = logging.getLogger(__name__)

NOISE_RE = re.compile(r"\[(?:music|âm nhạc|applause|vỗ tay|laughter|tiếng cười|nhạc)\]", re.I)
SENTENCE_END_RE = re.compile(r"[.!?…。]\s*$")


@dataclass
class Chunk:
    start: float
    end: float
    text: str


def clean_text(text: str) -> str:
    text = html.unescape(text).replace("\n", " ")
    text = NOISE_RE.sub(" ", text)
    return re.sub(r"\s+", " ", text).strip()


def chunk_segments(segments: list[Segment], target_sec: float = 45.0, max_sec: float = 75.0) -> list[Chunk]:
    """Merge subtitle lines into chunks of roughly `target_sec`.

    A chunk closes at the first sentence end after `target_sec`, or hard at `max_sec`
    (auto-generated subtitles often have no punctuation). Timestamps stay those of the
    original lines, so a citation always points at where the words were spoken.
    """
    chunks: list[Chunk] = []
    buf: list[str] = []
    start = end = None
    for seg in sorted(segments, key=lambda s: s.start):
        text = clean_text(seg.text)
        if not text:
            continue
        if start is None:
            start = seg.start
        buf.append(text)
        end = max(seg.end, end or seg.end)
        length = end - start
        if (length >= target_sec and SENTENCE_END_RE.search(text)) or length >= max_sec:
            chunks.append(Chunk(start, end, " ".join(buf)))
            buf, start, end = [], None, None
    if buf and start is not None:
        if chunks and (end - start) < target_sec / 3:
            last = chunks[-1]  # fold a tiny tail into the previous chunk
            chunks[-1] = Chunk(last.start, end, last.text + " " + " ".join(buf))
        else:
            chunks.append(Chunk(start, end, " ".join(buf)))
    return chunks


def whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


_whisper_cache: dict[str, object] = {}
_whisper_lock = threading.Lock()


def _whisper_model(model_size: str):
    """Load once per process: the model takes 10 s+ to load and is reused for every video."""
    with _whisper_lock:
        if model_size not in _whisper_cache:
            from faster_whisper import WhisperModel

            try:
                import ctranslate2

                cuda = ctranslate2.get_cuda_device_count() > 0
            except Exception:
                cuda = False
            device, compute = ("cuda", "int8_float16") if cuda else ("cpu", "int8")
            log.info("Loading Whisper %s on %s (%s)", model_size, device, compute)
            _whisper_cache[model_size] = WhisperModel(model_size, device=device, compute_type=compute)
        return _whisper_cache[model_size]


def transcribe_audio(
    audio_path: Path,
    model_size: str = "large-v3-turbo",
    language: str | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> tuple[list[Segment], str]:
    """Speech-to-text with faster-whisper. Returns (segments with timestamps, detected language).

    `language` = None lets Whisper detect it; pass "vi" / "en" to skip detection on mixed audio.
    `on_progress(fraction)` is called as segments come in (transcription is streamed).
    """
    if not whisper_available():
        raise TranscriptUnavailable(
            "Chưa cài faster-whisper (pip install faster-whisper) để chuyển giọng nói thành chữ")
    model = _whisper_model(model_size)
    segs, info = model.transcribe(str(audio_path), language=language or None, vad_filter=True,
                                  condition_on_previous_text=False)
    duration = float(getattr(info, "duration", 0) or 0)
    segments: list[Segment] = []
    last_report = 0.0
    for s in segs:  # generator: decoding happens while we iterate
        if s.text.strip():
            segments.append(Segment(float(s.start), float(s.end), s.text))
        if on_progress and duration and s.end - last_report >= 30:
            last_report = s.end
            on_progress(min(1.0, s.end / duration))
    if not segments:
        raise TranscriptUnavailable("Whisper không nhận ra lời nói nào trong video")
    return segments, info.language
