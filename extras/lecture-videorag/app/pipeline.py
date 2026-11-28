"""Ingestion and the per-video processing pipeline.

Stages: metadata -> transcript -> keyframes (+ slide reading) -> indexing -> notes.
Each stage commits its own transaction and updates video.status / progress, so the UI can show
progress and a crash leaves a clear state. Reprocessing a video replaces its data (idempotent).
The visual stage is best-effort: if it fails, the video still gets transcript search and notes.
"""
from __future__ import annotations

import base64
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
from sqlalchemy import delete, func, select

from . import frames as frames_mod
from . import localvideo
from . import transcript as transcript_mod
from . import youtube
from .llm import LLMError
from .models import Frame, Job, Note, Series, TranscriptChunk, Video
from .notes import generate_notes
from .services import Services

log = logging.getLogger(__name__)


# ---- ingestion ----------------------------------------------------------------------------------
def create_series(svc: Services, urls: list[str], title: str | None = None) -> int:
    """Expand playlist / video URLs into one series and queue every video. Raises InvalidYouTubeUrl."""
    parsed = [youtube.parse_youtube_url(u) for u in urls if u.strip()]  # validate all before any network call
    if not parsed:
        raise youtube.InvalidYouTubeUrl("Chưa có link nào")
    found_title = None
    infos: list[youtube.VideoInfo] = []
    for u in urls:
        if not u.strip():
            continue
        t, vids = youtube.expand(u)
        found_title = found_title or t
        infos.extend(vids)
    seen: set[str] = set()
    unique = [i for i in infos if not (i.youtube_id in seen or seen.add(i.youtube_id))]
    if not unique:
        raise youtube.InvalidYouTubeUrl("Playlist không có video nào truy cập được")
    with svc.db.session() as s:
        series = Series(title=title or found_title or f"Chuỗi {len(unique)} video", source_url="\n".join(urls))
        s.add(series)
        s.flush()
        for pos, info in enumerate(unique):
            v = Video(series_id=series.id, youtube_id=info.youtube_id, position=pos, title=info.title,
                      channel=info.channel, duration=info.duration, thumbnail_url=info.thumbnail_url)
            s.add(v)
            s.flush()
            s.add(Job(video_id=v.id))
        return series.id


def add_local_videos(svc: Services, sources: list[localvideo.LocalSource], title: str | None = None,
                     series_id: int | None = None) -> int:
    """Create a series of LMS videos (uploaded files / direct links), or append them to series_id."""
    if not sources:
        raise localvideo.InvalidVideoSource("Chưa có video nào")
    with svc.db.session() as s:
        if series_id is None:
            series = Series(title=title or f"Chuỗi {len(sources)} video", source_url=None)
            s.add(series)
            s.flush()
            series_id, start = series.id, 0
        else:
            if s.get(Series, series_id) is None:
                raise LookupError("Không có chuỗi bài giảng này")
            last = s.scalar(select(func.max(Video.position)).where(Video.series_id == series_id))
            start = 0 if last is None else last + 1
        for pos, src in enumerate(sources, start):
            v = Video(series_id=series_id, youtube_id=src.key, source_type="file", media_path=src.media_path,
                      source_url=src.source_url, position=pos, title=src.title, duration=src.duration)
            s.add(v)
            s.flush()
            s.add(Job(video_id=v.id))
        return series_id


def enqueue(svc: Services, video_id: int) -> bool:
    """Queue a (re)processing job unless one is already waiting or running for this video."""
    with svc.db.session() as s:
        active = s.scalars(select(Job).where(Job.video_id == video_id, Job.status.in_(("PENDING", "RUNNING")))).first()
        if active:
            return False
        v = s.get(Video, video_id)
        if v is None:
            raise LookupError("Không có video này")
        v.status, v.progress, v.error_message, v.warning = "PENDING", 0, None, None
        s.add(Job(video_id=video_id))
        return True


# ---- processing ---------------------------------------------------------------------------------
def _set(svc: Services, video_id: int, **fields) -> None:
    with svc.db.session() as s:
        v = s.get(Video, video_id)
        for k, val in fields.items():
            setattr(v, k, val)


def process_video(svc: Services, video_id: int) -> None:
    st = svc.settings
    with svc.db.session() as s:
        v = s.get(Video, video_id)
        yid, need_meta, is_file = v.youtube_id, not v.title or not v.duration, v.is_file

    # 1. metadata (LMS file: download the direct link if needed, read the duration from the file)
    _set(svc, video_id, status="FETCHING_METADATA", progress=5, error_message=None, warning=None)
    local_path = _prepare_local_file(svc, video_id) if is_file else None
    if need_meta and not is_file:
        try:
            info = youtube.fetch_metadata(yid)
            _set(svc, video_id, title=info.title, channel=info.channel, duration=info.duration,
                 thumbnail_url=info.thumbnail_url)
        except Exception as e:  # metadata is nice-to-have; the subtitles call will tell if the video is gone
            log.warning("metadata failed for %s: %s", yid, e)

    # 2. transcript
    _set(svc, video_id, status="FETCHING_TRANSCRIPT", progress=15)
    if local_path is not None:
        segments, lang, source = _transcribe_file(svc, video_id, local_path)
    else:
        segments, lang, source = _get_transcript(svc, video_id, yid)
    chunks = transcript_mod.chunk_segments(segments, st.chunk_target_sec, st.chunk_max_sec)
    with svc.db.session() as s:
        svc.index.remove_video(s, video_id)
        s.execute(delete(TranscriptChunk).where(TranscriptChunk.video_id == video_id))
        s.execute(delete(Note).where(Note.video_id == video_id))
        for i, c in enumerate(chunks):
            s.add(TranscriptChunk(video_id=video_id, idx=i, start=c.start, end_time=c.end, text=c.text, language=lang))
        v = s.get(Video, video_id)
        v.language, v.transcript_source, v.progress = lang, source, 30
        if not v.duration and chunks:
            v.duration = chunks[-1].end

    # 3. keyframes + slide reading (best effort)
    _set(svc, video_id, status="PROCESSING_FRAMES", progress=35)
    try:
        n = _process_frames(svc, video_id, yid, local_path)
        log.info("video %s: %d keyframes", yid, n)
    except Exception as e:
        log.exception("frames failed for %s", yid)
        _set(svc, video_id, warning=f"Bỏ qua phần hình ảnh: {e}")

    # 4. index
    _set(svc, video_id, status="INDEXING", progress=75)
    with svc.db.session() as s:
        svc.index.index_video(s, s.get(Video, video_id))

    # 5. notes
    _set(svc, video_id, status="SUMMARIZING", progress=85)
    generate_notes(svc, video_id)
    _set(svc, video_id, status="COMPLETED", progress=100)


def _prepare_local_file(svc: Services, video_id: int) -> Path:
    """Return the stored file of an LMS video, downloading its direct link first if needed."""
    st = svc.settings
    with svc.db.session() as s:
        v = s.get(Video, video_id)
        key, media_path, source_url, duration = v.youtube_id, v.media_path, v.source_url, v.duration
    path = st.uploads_dir / media_path if media_path else None
    if path is None or not path.exists():
        if not source_url:
            raise localvideo.InvalidVideoSource("Không còn file video trên máy, hãy tải lên lại")
        path = localvideo.download_url(source_url, st.uploads_dir, key, st.max_upload_mb << 20,
                                       st.download_timeout_sec)
        _set(svc, video_id, media_path=path.name, progress=12)
    if not duration:
        _set(svc, video_id, duration=localvideo.probe(path))
    return path


def _transcribe_file(svc: Services, video_id: int, path: Path) -> tuple[list, str, str]:
    """LMS videos have no subtitles: Whisper reads the audio track straight from the stored file."""
    st = svc.settings
    if not localvideo.has_audio(path):
        raise youtube.TranscriptUnavailable("File video không có âm thanh nên không chuyển được lời giảng thành chữ")
    segments, lang = transcript_mod.transcribe_audio(
        path, st.whisper_model, st.whisper_language or None,
        on_progress=lambda f: _set(svc, video_id, progress=15 + int(f * 15)))  # 15% -> 30%
    return segments, lang, "whisper"


def _get_transcript(svc: Services, video_id: int, yid: str) -> tuple[list, str, str]:
    """Return (segments, language, source) according to settings.transcript_mode."""
    st = svc.settings
    mode = st.transcript_mode
    if mode not in ("auto", "whisper", "subtitles"):
        raise ValueError(f"LVR_TRANSCRIPT_MODE không hợp lệ: {mode}")
    if mode in ("auto", "subtitles"):
        try:
            return youtube.fetch_subtitles(yid, st.transcript_languages)
        except youtube.TranscriptUnavailable as sub_err:
            if mode == "subtitles":
                raise
            if not transcript_mod.whisper_available():
                raise youtube.TranscriptUnavailable(
                    f"{sub_err}. Cài faster-whisper để tự chuyển giọng nói thành chữ.") from sub_err
            log.info("no subtitles for %s (%s), using speech-to-text", yid, sub_err)

    # Whisper: download the audio stream only (no ffmpeg needed: faster-whisper decodes it itself)
    audio = youtube.download_audio(yid, st.media_dir)
    _set(svc, video_id, progress=18)
    try:
        segments, lang = transcript_mod.transcribe_audio(
            audio, st.whisper_model, st.whisper_language or None,
            on_progress=lambda f: _set(svc, video_id, progress=18 + int(f * 12)))  # 18% -> 30%
    finally:
        audio.unlink(missing_ok=True)
    return segments, lang, "whisper"


FRAME_SCHEMA = {
    "type": "object",
    "properties": {
        "has_content": {"type": "boolean"},
        "slide_text": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["has_content", "slide_text", "summary"],
    "additionalProperties": False,
}

FRAME_SYSTEM = """You read one frame of a lecture video.
- "has_content": true if the frame shows anything a student could learn from or cite: slides,
  board writing, code, a diagram, a chart, a formula, a worked example, a demo, or a labelled
  illustration of the topic. False only when it carries no lesson material: blank or transition
  screen, only the speaker, decorative characters or jokes with no explanation, credits/sponsor
  lists, social media pages, ads.
- "slide_text": ALL text visible in the frame (slides, board, labels, speech bubbles, captions),
  transcribed exactly, even when has_content is false (keep formulas, code and line breaks; use
  plain text math such as x^2, sum_i). Empty string only if there is no text at all.
- "summary": one or two sentences describing what the visual shows (diagram structure, what a
  chart compares, what the code does). {language}"""


def _process_frames(svc: Services, video_id: int, yid: str, local_path: Path | None = None) -> int:
    st = svc.settings
    out_dir = st.frames_dir / yid
    with svc.db.session() as s:
        s.execute(delete(Frame).where(Frame.video_id == video_id))
    shutil.rmtree(out_dir, ignore_errors=True)

    video_path = local_path or youtube.download_video(yid, st.media_dir, st.video_max_height)
    try:
        _set(svc, video_id, progress=45)
        keyframes = frames_mod.extract_keyframes(
            video_path, st.frame_sample_sec, st.frame_diff_threshold, st.frame_min_gap_sec, st.max_frames_per_video)
    finally:
        if local_path is None and not st.keep_video_files:  # LMS files are kept for in-app playback
            video_path.unlink(missing_ok=True)

    records = []
    for i, k in enumerate(keyframes):
        rel = f"{yid}/{i:04d}_{int(k.timestamp)}.jpg"
        frames_mod.save_jpeg(k.image, st.frames_dir / rel)
        records.append((i, k, rel))
    _set(svc, video_id, progress=55)

    descriptions: dict[int, dict] = {}
    if st.describe_frames and records:
        def describe(item):
            i, k, rel = item
            ok, buf = cv2.imencode(".jpg", _shrink(k.image), [cv2.IMWRITE_JPEG_QUALITY, 85])
            img_b64 = base64.standard_b64encode(buf.tobytes()).decode()
            res = svc.call_llm(
                purpose="frame", video_id=video_id,
                system=FRAME_SYSTEM.format(language="Write the summary in the language of the slide."),
                content=[{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}},
                         {"type": "text", "text": "Read this lecture frame."}],
                schema=FRAME_SCHEMA, effort=st.effort_frames, max_tokens=4000,
            )
            return i, res.data

        errors = 0
        with ThreadPoolExecutor(max_workers=max(1, st.llm_concurrency)) as pool:
            for fut in [pool.submit(describe, r) for r in records]:
                try:
                    i, data = fut.result()
                    descriptions[i] = data
                except LLMError as e:
                    errors += 1
                    log.warning("frame description failed: %s", e)
        if errors:
            _set(svc, video_id, warning=f"{errors}/{len(records)} khung hình không đọc được bằng model")

    with svc.db.session() as s:
        for i, k, rel in records:
            d = descriptions.get(i, {})
            s.add(Frame(video_id=video_id, idx=i, timestamp=k.timestamp, image_path=rel, image_hash=k.dhash,
                        slide_text=(d.get("slide_text") or "").strip() or None,
                        summary=(d.get("summary") or "").strip() or None,
                        has_content=d.get("has_content") if d else None))
        v = s.get(Video, video_id)
        if v.is_file and records:  # no YouTube thumbnail: use the first slide with lesson content
            first = next((rel for i, _k, rel in records if descriptions.get(i, {}).get("has_content", True)),
                         records[0][2])
            v.thumbnail_url = "/media/frames/" + first
    _set(svc, video_id, progress=70)
    return len(records)


def _shrink(img, max_width: int = 1280):
    h, w = img.shape[:2]
    if w <= max_width:
        return img
    return cv2.resize(img, (max_width, int(h * max_width / w)), interpolation=cv2.INTER_AREA)


def delete_video_files(svc: Services, youtube_id: str, media_path: str | None = None) -> None:
    path: Path = svc.settings.frames_dir / youtube_id
    shutil.rmtree(path, ignore_errors=True)
    localvideo.remove_file(svc.settings.uploads_dir, media_path)
