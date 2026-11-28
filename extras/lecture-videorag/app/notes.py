"""Knowledge notes for one lecture video: summary + topics + points, each point with citations."""
from __future__ import annotations

import json
import logging

from sqlalchemy import select

from .citations import fmt_time, resolve_refs
from .models import Frame, Note, TranscriptChunk, Video
from .search import frame_text
from .services import Services

log = logging.getLogger(__name__)

NOTES_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "points": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "refs": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["text", "refs"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["title", "points"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "topics"],
    "additionalProperties": False,
}

NOTES_SYSTEM = """You turn one lecture video into study notes that a student can verify.

You get the transcript in numbered chunks [C<id>] with their time ranges, and the slides / board
content in numbered keyframes [F<id>] with the time they appear.

Rules:
- Use only knowledge that is in this lecture. Do not add facts from outside it.
- Group points into topics in the order the lecture covers them.
- Each point is one self-contained piece of knowledge (definition, idea, formula, step, example,
  warning), written so it can be understood without watching the video. Keep formulas, code and
  numbers exactly as given; write formulas in plain text (e.g. sigma(w1*a1 + ... + wn*an + b)), never LaTeX.
- Every point must cite in "refs" the id(s) where it is explained: one or more C ids, plus the F id
  of the slide when the slide shows the formula, diagram or text the point relies on.
- Cite only ids that appear in the input. Never invent an id. If you cannot cite a point, drop it.
- "summary": 2 to 4 sentences on what the lecture teaches.
{language}"""


def build_context(video: Video, chunks: list[TranscriptChunk], frames: list[Frame]) -> str:
    lines = [f"Lecture title: {video.title or video.youtube_id}", "", "<transcript>"]
    for c in chunks:
        lines.append(f"[C{c.id}] ({fmt_time(c.start)}–{fmt_time(c.end_time)}) {c.text}")
    lines.append("</transcript>")
    content_frames = [f for f in frames if f.has_content is not False and frame_text(f)]
    if content_frames:
        lines += ["", "<slides>"]
        for f in content_frames:
            lines.append(f"[F{f.id}] ({fmt_time(f.timestamp)}) {frame_text(f)}")
        lines.append("</slides>")
    return "\n".join(lines)


def generate_notes(svc: Services, video_id: int) -> dict:
    with svc.db.session() as s:
        video = s.get(Video, video_id)
        chunks = s.scalars(select(TranscriptChunk).where(TranscriptChunk.video_id == video_id)
                           .order_by(TranscriptChunk.start)).all()
        frames = s.scalars(select(Frame).where(Frame.video_id == video_id).order_by(Frame.timestamp)).all()
        if not chunks:
            raise ValueError("Video chưa có transcript")
        context = build_context(video, chunks, frames)

    res = svc.call_llm(
        purpose="notes",
        video_id=video_id,
        system=NOTES_SYSTEM.format(language=svc.language_instruction()),
        content=[{"type": "text", "text": context}],
        schema=NOTES_SCHEMA,
        effort=svc.settings.effort_notes,
        max_tokens=32000,
    )
    data = res.data
    all_refs = [r for t in data.get("topics", []) for p in t.get("points", []) for r in p.get("refs", [])]

    with svc.db.session() as s:
        cites = resolve_refs(s, all_refs, {video_id})
        dropped = 0
        topics = []
        for t in data.get("topics", []):
            points = []
            for p in t.get("points", []):
                refs = [r for r in dict.fromkeys(p.get("refs", [])) if r in cites]
                if not refs:
                    dropped += 1  # an uncited point is not verifiable: leave it out
                    continue
                points.append({"text": p.get("text", "").strip(), "citations": [cites[r] for r in refs]})
            if points:
                topics.append({"title": t.get("title", "").strip(), "points": points})
        note = {
            "summary": data.get("summary", "").strip(),
            "topics": topics,
            "dropped_uncited_points": dropped,
            "model": res.model,
        }
        existing = s.scalars(select(Note).where(Note.video_id == video_id)).first()
        if existing:
            existing.content_json = json.dumps(note, ensure_ascii=False)
            existing.model = res.model
        else:
            s.add(Note(video_id=video_id, content_json=json.dumps(note, ensure_ascii=False), model=res.model))
    if dropped:
        log.warning("video %s: dropped %d uncited note points", video_id, dropped)
    return note
