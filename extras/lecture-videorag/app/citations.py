"""Turn model-cited ids ("C12" = transcript chunk 12, "F3" = keyframe 3) into checkable citations.

The model never writes timestamps itself: it cites ids from the context it was given, and this
module looks the ids up in the database. Ids that do not exist in the allowed scope are dropped,
so a citation can be wrong only if the model picked the wrong passage, never an invented time.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Frame, TranscriptChunk, Video

REF_RE = re.compile(r"\b([CF])(\d+)\b")
INLINE_REF_RE = re.compile(r"\[([CF]\d+(?:\s*,\s*[CF]\d+)*)\]")


def fmt_time(sec: float) -> str:
    sec = int(sec or 0)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def frame_url(f: Frame) -> str:
    return "/media/frames/" + f.image_path


def nearest_frame(s: Session, video_id: int, t: float, back: float = 180.0) -> Frame | None:
    """The slide on screen at time t: latest content keyframe shown at or shortly before t."""
    stmt = (
        select(Frame)
        .where(Frame.video_id == video_id, Frame.timestamp <= t + 5, Frame.timestamp >= t - back,
               Frame.has_content.is_not(False))
        .order_by(Frame.timestamp.desc())
        .limit(1)
    )
    return s.scalars(stmt).first()


def resolve_refs(s: Session, refs: list[str], video_ids: set[int]) -> dict[str, dict]:
    chunk_ids = [int(r[1:]) for r in refs if r.startswith("C") and r[1:].isdigit()]
    frame_ids = [int(r[1:]) for r in refs if r.startswith("F") and r[1:].isdigit()]
    chunks = s.scalars(select(TranscriptChunk).where(TranscriptChunk.id.in_(chunk_ids))).all() if chunk_ids else []
    frames = s.scalars(select(Frame).where(Frame.id.in_(frame_ids))).all() if frame_ids else []
    videos = {v.id: v for v in s.scalars(select(Video).where(Video.id.in_(video_ids)))} if video_ids else {}
    out: dict[str, dict] = {}
    for c in chunks:
        if c.video_id not in video_ids:
            continue
        v = videos[c.video_id]
        f = nearest_frame(s, c.video_id, c.start)
        out[f"C{c.id}"] = _citation(f"C{c.id}", "transcript", v, c.start, c.end_time, c.text, f)
    for f in frames:
        if f.video_id not in video_ids:
            continue
        v = videos[f.video_id]
        out[f"F{f.id}"] = _citation(f"F{f.id}", "slide", v, f.timestamp, f.timestamp, f.slide_text or f.summary, f)
    return out


def _citation(ref: str, kind: str, v: Video, start: float, end: float, quote: str | None, f: Frame | None) -> dict:
    return {
        "ref": ref,
        "kind": kind,
        "video_id": v.id,
        "youtube_id": v.youtube_id,
        "video_title": v.title,
        "position": v.position,
        "start": round(start, 1),
        "end": round(end, 1),
        "label": fmt_time(start) if kind == "slide" else f"{fmt_time(start)}–{fmt_time(end)}",
        "source_type": v.source_type,
        "url": v.link_at(start),
        "quote": (quote or "")[:400],
        "frame_url": frame_url(f) if f else None,
        "frame_time": round(f.timestamp, 1) if f else None,
    }


def refs_in_text(text: str) -> list[str]:
    found: list[str] = []
    for group in INLINE_REF_RE.findall(text or ""):
        for r in re.split(r"\s*,\s*", group):
            if r not in found:
                found.append(r)
    return found


def strip_invalid_inline_refs(text: str, valid: set[str]) -> str:
    def repl(m: re.Match) -> str:
        keep = [r for r in re.split(r"\s*,\s*", m.group(1)) if r in valid]
        return "[" + ", ".join(keep) + "]" if keep else ""

    return re.sub(r"\s+([.,;:])", r"\1", INLINE_REF_RE.sub(repl, text or ""))
