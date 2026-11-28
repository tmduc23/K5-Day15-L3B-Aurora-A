"""Question answering over a whole lecture series, grounded in retrieved transcript and slides."""
from __future__ import annotations

import json
import logging

from sqlalchemy import select

from .citations import fmt_time, refs_in_text, resolve_refs, strip_invalid_inline_refs
from .models import ChatMessage, ChatSession, Frame, TranscriptChunk, Video
from .search import TimeSegment, frame_text, group_segments
from .services import Services

log = logging.getLogger(__name__)

CHAT_SCHEMA = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "insufficient_evidence": {"type": "boolean"},
    },
    "required": ["answer", "insufficient_evidence"],
    "additionalProperties": False,
}

CHAT_SYSTEM = """You are a teaching assistant for a series of lecture videos. Answer the student's
question using only the lecture excerpts provided.

The excerpts are transcript chunks [C<id>] and slide / board keyframes [F<id>], each with its video
and time. Rules:
- Put a citation right after each claim, in square brackets with the id: [C12] or [C12, F3].
  Cite only ids that appear in the excerpts.
- If the excerpts do not contain the answer, say clearly that the lecture series does not cover it
  (or not in the parts found), set "insufficient_evidence" to true, and do not answer from general
  knowledge.
- If the excerpts answer only part of the question, answer that part and say what is missing.
- Be concise and clear. Use short paragraphs or bullet points.
- Write formulas in plain text, never LaTeX: e.g. Cost = (a1 - y1)^2 + (a2 - y2)^2 + ... + (an - yn)^2.
- Mention which video (by its number/title) when the answer spans several videos.
{language}"""

NO_EVIDENCE = {
    "vi": "Mình không tìm thấy đoạn nào trong chuỗi bài giảng nói về nội dung này.",
    "en": "I could not find any part of this lecture series that covers this.",
}


def _context(svc: Services, segments: list[TimeSegment], pad: float = 20.0) -> tuple[str, set[int]]:
    blocks: list[str] = []
    video_ids: set[int] = set()
    with svc.db.session() as s:
        for seg in segments:
            v = s.get(Video, seg.video_id)
            video_ids.add(v.id)
            chunks = s.scalars(
                select(TranscriptChunk)
                .where(TranscriptChunk.video_id == v.id,
                       TranscriptChunk.end_time >= seg.start - pad,
                       TranscriptChunk.start <= seg.end + pad)
                .order_by(TranscriptChunk.start)
            ).all()
            frames = s.scalars(
                select(Frame)
                .where(Frame.video_id == v.id, Frame.timestamp >= seg.start - 60, Frame.timestamp <= seg.end + 10,
                       Frame.has_content.is_not(False))
                .order_by(Frame.timestamp)
            ).all()
            lines = [f"### Video {v.position + 1}: {v.title or v.youtube_id} "
                     f"({fmt_time(seg.start)}–{fmt_time(seg.end)})"]
            lines += [f"[C{c.id}] ({fmt_time(c.start)}–{fmt_time(c.end_time)}) {c.text}" for c in chunks]
            lines += [f"[F{f.id}] (slide at {fmt_time(f.timestamp)}) {frame_text(f)}" for f in frames if frame_text(f)]
            blocks.append("\n".join(lines))
    return "\n\n".join(blocks), video_ids


def ask(svc: Services, session_id: int, question: str, video_ids: list[int] | None = None) -> dict:
    question = question.strip()
    if not question:
        raise ValueError("Câu hỏi trống")
    with svc.db.session() as s:
        session = s.get(ChatSession, session_id)
        if session is None:
            raise LookupError("Không có phiên chat này")
        series_id = session.series_id
        history = [(m.role, m.content) for m in session.messages[-6:]]
        s.add(ChatMessage(session_id=session_id, role="user", content=question))
        if not history:
            session.title = question[:120]

    # Short follow-ups ("còn cái kia thì sao?") need the previous question to retrieve well.
    query = question
    prev_user = [c for r, c in history if r == "user"]
    if prev_user and len(question.split()) < 8:
        query = prev_user[-1] + " " + question

    hits = svc.index.search(series_id, query, video_ids=video_ids, top_k=svc.settings.search_top_k * 2)
    segments = group_segments(hits)[: svc.settings.chat_context_segments]

    citations: list[dict] = []
    if not segments:
        lang = "en" if svc.settings.output_language == "en" else "vi"
        answer, insufficient = NO_EVIDENCE[lang], True
    else:
        context, scope = _context(svc, segments)
        convo = "\n".join(f"{'Student' if r == 'user' else 'Assistant'}: {c}" for r, c in history)
        prompt = (f"<excerpts>\n{context}\n</excerpts>\n\n"
                  + (f"<conversation_so_far>\n{convo}\n</conversation_so_far>\n\n" if convo else "")
                  + f"Question: {question}")
        res = svc.call_llm(
            purpose="chat",
            system=CHAT_SYSTEM.format(language=svc.language_instruction()),
            content=[{"type": "text", "text": prompt}],
            schema=CHAT_SCHEMA,
            effort=svc.settings.effort_chat,
        )
        raw = res.data.get("answer", "")
        insufficient = bool(res.data.get("insufficient_evidence"))
        with svc.db.session() as s:
            cites = resolve_refs(s, refs_in_text(raw), scope)
        answer = strip_invalid_inline_refs(raw, set(cites))
        citations = [cites[r] for r in refs_in_text(answer)]

    with svc.db.session() as s:
        msg = ChatMessage(session_id=session_id, role="assistant", content=answer,
                          citations_json=json.dumps({"citations": citations, "insufficient_evidence": insufficient},
                                                    ensure_ascii=False))
        s.add(msg)
        s.flush()
        return message_dict(msg)


def message_dict(m: ChatMessage) -> dict:
    extra = json.loads(m.citations_json) if m.citations_json else {}
    return {
        "id": m.id,
        "role": m.role,
        "content": m.content,
        "citations": extra.get("citations", []),
        "insufficient_evidence": extra.get("insufficient_evidence", False),
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
