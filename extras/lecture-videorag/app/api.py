"""REST API. Route handlers stay thin: validation in, service call, serialisation out."""
from __future__ import annotations

import json
import logging
import os

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from . import chat as chat_mod
from . import localvideo, pipeline, transcript, youtube
from .citations import fmt_time, frame_url, resolve_refs
from .llm import LLMError
from .models import ChatSession, Frame, Job, LlmCall, Series, TranscriptChunk, Video
from .search import group_segments
from .services import Services

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def svc(request: Request) -> Services:
    return request.app.state.services


# ---- schemas ------------------------------------------------------------------------------------
class SeriesIn(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=50)
    title: str | None = Field(default=None, max_length=300)


class LinksIn(BaseModel):
    """Direct links to LMS video files (not YouTube), downloaded by the worker."""
    urls: list[str] = Field(min_length=1, max_length=50)
    title: str | None = Field(default=None, max_length=300)
    series_id: int | None = None


class SearchIn(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    video_ids: list[int] | None = None
    mode: str = Field(default="hybrid", pattern="^(hybrid|dense|keyword)$")
    top_k: int = Field(default=10, ge=1, le=50)


class QuestionIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    video_ids: list[int] | None = None


# ---- serialisers --------------------------------------------------------------------------------
def video_dict(v: Video) -> dict:
    return {
        "id": v.id, "series_id": v.series_id, "youtube_id": v.youtube_id, "source_type": v.source_type,
        "position": v.position,
        "title": v.title, "channel": v.channel, "duration": v.duration, "thumbnail_url": v.thumbnail_url,
        "language": v.language, "transcript_source": v.transcript_source, "status": v.status,
        "progress": v.progress, "error_message": v.error_message, "warning": v.warning, "url": v.url,
        "media_url": v.link_at(0) if v.is_file and v.media_path else None,
    }


def series_dict(s: Series, with_videos: bool = False) -> dict:
    vids = list(s.videos)
    out = {
        "id": s.id, "title": s.title, "created_at": s.created_at.isoformat(),
        "video_count": len(vids),
        "completed": sum(v.status == "COMPLETED" for v in vids),
        "failed": sum(v.status == "FAILED" for v in vids),
    }
    if with_videos:
        out["videos"] = [video_dict(v) for v in vids]
    return out


# ---- routes -------------------------------------------------------------------------------------
@router.get("/health")
def health(request: Request):
    st = svc(request).settings
    keys = {
        "openai": bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
        "fake": True,
    }
    return {
        "status": "ok",
        "llm_provider": st.llm_provider,
        "llm_model": svc(request).llm.model,
        "api_key_configured": keys.get(st.llm_provider, False),
        "embedding_model": svc(request).embedder.name,
        "whisper_available": transcript.whisper_available(),
        "output_language": st.output_language,
    }


@router.get("/stats")
def stats(request: Request):
    with svc(request).db.session() as s:
        by_status = dict(s.execute(select(Video.status, func.count()).group_by(Video.status)).all())
        tokens = s.execute(select(func.coalesce(func.sum(LlmCall.input_tokens), 0),
                                  func.coalesce(func.sum(LlmCall.output_tokens), 0))).one()
        return {
            "series": s.scalar(select(func.count()).select_from(Series)),
            "videos": sum(by_status.values()),
            "videos_by_status": by_status,
            "frames": s.scalar(select(func.count()).select_from(Frame)),
            "transcript_chunks": s.scalar(select(func.count()).select_from(TranscriptChunk)),
            "llm_input_tokens": tokens[0],
            "llm_output_tokens": tokens[1],
        }


@router.post("/series", status_code=201)
def create_series(body: SeriesIn, request: Request):
    try:
        sid = pipeline.create_series(svc(request), body.urls, body.title)
    except youtube.InvalidYouTubeUrl as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # yt-dlp network / unavailable playlist
        log.exception("create_series failed")
        raise HTTPException(502, f"Không đọc được danh sách video từ YouTube: {e}")
    with svc(request).db.session() as s:
        return series_dict(s.get(Series, sid), with_videos=True)


@router.post("/series/upload", status_code=201)
def upload_videos(request: Request, files: list[UploadFile] = File(...), title: str | None = Form(None),
                  series_id: int | None = Form(None)):
    """LMS lecture videos as files: new series, or appended to series_id. Files are sorted by name."""
    sv = svc(request)
    if not files or len(files) > 50:
        raise HTTPException(400, "Chọn từ 1 đến 50 file video")
    try:
        for f in files:
            localvideo.check_extension(f.filename)
    except localvideo.InvalidVideoSource as e:
        raise HTTPException(400, str(e))
    if series_id is not None:
        with sv.db.session() as s:
            if s.get(Series, series_id) is None:
                raise HTTPException(404, "Không có chuỗi bài giảng này")
    sources, saved = [], []
    try:
        for f in sorted(files, key=lambda f: localvideo.natural_key(f.filename)):
            key = localvideo.new_key()
            dest = sv.settings.uploads_dir / f"{key}{localvideo.check_extension(f.filename)}"
            localvideo.save_stream(f.file, dest, sv.settings.max_upload_mb << 20)
            saved.append(dest)
            try:
                duration = localvideo.probe(dest)
            except localvideo.InvalidVideoSource as e:
                raise localvideo.InvalidVideoSource(f"'{f.filename}': {e}") from e
            sources.append(localvideo.LocalSource(key, localvideo.title_from_filename(f.filename),
                                                  media_path=dest.name, duration=duration))
        sid = pipeline.add_local_videos(sv, sources, (title or "").strip() or None, series_id)
    except localvideo.InvalidVideoSource as e:
        for p in saved:
            p.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    except BaseException:
        for p in saved:
            p.unlink(missing_ok=True)
        raise
    with sv.db.session() as s:
        return series_dict(s.get(Series, sid), with_videos=True)


@router.post("/series/links", status_code=201)
def add_links(body: LinksIn, request: Request):
    """LMS lecture videos as direct file links (the worker downloads them)."""
    sv = svc(request)
    try:
        urls = [localvideo.check_direct_url(u) for u in body.urls if u.strip()]
        sources = [localvideo.LocalSource(localvideo.new_key(), localvideo.title_from_url(u), source_url=u)
                   for u in urls]
        sid = pipeline.add_local_videos(sv, sources, body.title, body.series_id)
    except localvideo.InvalidVideoSource as e:
        raise HTTPException(400, str(e))
    except LookupError as e:
        raise HTTPException(404, str(e))
    with sv.db.session() as s:
        return series_dict(s.get(Series, sid), with_videos=True)


@router.get("/series")
def list_series(request: Request):
    with svc(request).db.session() as s:
        return [series_dict(x) for x in s.scalars(select(Series).order_by(Series.id.desc()))]


@router.get("/series/{series_id}")
def get_series(series_id: int, request: Request):
    with svc(request).db.session() as s:
        x = s.get(Series, series_id)
        if x is None:
            raise HTTPException(404, "Không có chuỗi bài giảng này")
        return series_dict(x, with_videos=True)


@router.delete("/series/{series_id}", status_code=204)
def delete_series(series_id: int, request: Request):
    sv = svc(request)
    with sv.db.session() as s:
        x = s.get(Series, series_id)
        if x is None:
            raise HTTPException(404, "Không có chuỗi bài giảng này")
        files = [(v.youtube_id, v.media_path) for v in x.videos]
        for v in x.videos:
            sv.index.remove_video(s, v.id)
        s.delete(x)
    for yid, media_path in files:
        pipeline.delete_video_files(sv, yid, media_path)


@router.get("/videos/{video_id}")
def get_video(video_id: int, request: Request):
    with svc(request).db.session() as s:
        v = s.get(Video, video_id)
        if v is None:
            raise HTTPException(404, "Không có video này")
        out = video_dict(v)
        out["notes"] = json.loads(v.note.content_json) if v.note else None
        out["frames"] = [
            {"id": f.id, "timestamp": f.timestamp, "label": fmt_time(f.timestamp), "url": frame_url(f),
             "slide_text": f.slide_text, "summary": f.summary, "has_content": f.has_content}
            for f in v.frames
        ]
        out["transcript"] = [
            {"id": c.id, "start": c.start, "end": c.end_time, "label": fmt_time(c.start), "text": c.text}
            for c in v.chunks
        ]
        last_job = s.scalars(select(Job).where(Job.video_id == v.id).order_by(Job.id.desc())).first()
        out["job"] = None if last_job is None else {
            "id": last_job.id, "status": last_job.status, "attempts": last_job.attempts,
            "error_message": last_job.error_message,
        }
        return out


@router.post("/videos/{video_id}/reprocess", status_code=202)
def reprocess(video_id: int, request: Request):
    try:
        queued = pipeline.enqueue(svc(request), video_id)
    except LookupError as e:
        raise HTTPException(404, str(e))
    return {"queued": queued}


@router.delete("/videos/{video_id}", status_code=204)
def delete_video(video_id: int, request: Request):
    sv = svc(request)
    with sv.db.session() as s:
        v = s.get(Video, video_id)
        if v is None:
            raise HTTPException(404, "Không có video này")
        yid, media_path = v.youtube_id, v.media_path
        sv.index.remove_video(s, v.id)
        s.delete(v)
    pipeline.delete_video_files(sv, yid, media_path)


@router.post("/series/{series_id}/search")
def search(series_id: int, body: SearchIn, request: Request):
    sv = svc(request)
    hits = sv.index.search(series_id, body.query, body.video_ids, body.top_k, body.mode)
    with sv.db.session() as s:
        scope = {h.video_id for h in hits}
        cites = resolve_refs(s, [h.ref for h in hits], scope)
    results = [dict(cites[h.ref], score=round(h.score, 4), matched_by=h.sources) for h in hits if h.ref in cites]
    segments = [
        {"video_id": g.video_id, "start": g.start, "end": g.end,
         "label": f"{fmt_time(g.start)}–{fmt_time(g.end)}", "refs": [h.ref for h in g.hits]}
        for g in group_segments(hits)
    ]
    return {"results": results, "segments": segments}


@router.post("/series/{series_id}/chat/sessions", status_code=201)
def new_session(series_id: int, request: Request):
    with svc(request).db.session() as s:
        if s.get(Series, series_id) is None:
            raise HTTPException(404, "Không có chuỗi bài giảng này")
        cs = ChatSession(series_id=series_id)
        s.add(cs)
        s.flush()
        return {"id": cs.id, "series_id": series_id, "title": cs.title, "messages": []}


@router.get("/series/{series_id}/chat/sessions")
def list_sessions(series_id: int, request: Request):
    with svc(request).db.session() as s:
        rows = s.scalars(select(ChatSession).where(ChatSession.series_id == series_id)
                         .order_by(ChatSession.id.desc())).all()
        return [{"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()} for c in rows]


@router.get("/chat/sessions/{session_id}")
def get_session(session_id: int, request: Request):
    with svc(request).db.session() as s:
        cs = s.get(ChatSession, session_id)
        if cs is None:
            raise HTTPException(404, "Không có phiên chat này")
        return {"id": cs.id, "series_id": cs.series_id, "title": cs.title,
                "messages": [chat_mod.message_dict(m) for m in cs.messages]}


@router.post("/chat/sessions/{session_id}/messages")
def post_message(session_id: int, body: QuestionIn, request: Request):
    try:
        return chat_mod.ask(svc(request), session_id, body.question, body.video_ids)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except LLMError as e:
        raise HTTPException(502, str(e))
