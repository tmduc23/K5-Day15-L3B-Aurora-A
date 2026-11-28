from __future__ import annotations

import json

from sqlalchemy import func, select, text

from app import chat
from app.models import ChatSession, Note, Series
from app.notes import generate_notes
from app.search import Hit, group_segments


def test_hybrid_search_finds_right_video(svc, series_with_videos):
    sid, va, vb = series_with_videos
    hits = svc.index.search(sid, "learning rate quá lớn")
    assert hits and hits[0].video_id == va
    hits = svc.index.search(sid, "pooling CNN")
    assert hits[0].video_id == vb


def test_keyword_search_ignores_diacritics(svc, series_with_videos):
    sid, va, _ = series_with_videos
    hits = svc.index.search(sid, "ham mat mat", mode="keyword")  # typed without accents
    assert hits and hits[0].video_id == va and "mất mát" in hits[0].text


def test_search_finds_slide_text(svc, series_with_videos):
    sid, va, _ = series_with_videos
    hits = svc.index.search(sid, "dao động alpha", top_k=20)
    assert any(h.kind == "frame" and h.video_id == va for h in hits)


def test_search_video_filter_and_scope(svc, series_with_videos):
    sid, va, vb = series_with_videos
    hits = svc.index.search(sid, "learning rate", video_ids=[vb])
    assert all(h.video_id == vb for h in hits)
    assert svc.index.search(sid + 999, "learning rate") == []


def test_group_segments_merges_nearby_hits():
    hits = [Hit("chunk", 1, 7, 0, 40, "", 0.5), Hit("chunk", 2, 7, 60, 90, "", 0.4),
            Hit("chunk", 3, 7, 400, 430, "", 1.2), Hit("chunk", 4, 8, 10, 20, "", 0.1)]
    segs = group_segments(hits, window=60)
    assert [(g.video_id, g.start, g.end) for g in segs] == [(7, 400, 430), (7, 0, 90), (8, 10, 20)]


def test_reindex_is_idempotent(svc, series_with_videos):
    sid, va, _ = series_with_videos
    from app.models import Video

    count = lambda s: s.execute(text("SELECT count(*) FROM search_fts WHERE video_id=:v"), {"v": va}).scalar()
    with svc.db.session() as s:
        before = count(s)
        svc.index.index_video(s, s.get(Video, va))
    with svc.db.session() as s:
        assert count(s) == before == 4  # 3 chunks + 1 slide


def test_notes_keep_only_verifiable_points(svc, fake_llm, series_with_videos):
    sid, va, vb = series_with_videos
    with svc.db.session() as s:
        from app.models import TranscriptChunk

        c_ids = s.scalars(select(TranscriptChunk.id).where(TranscriptChunk.video_id == va)
                          .order_by(TranscriptChunk.start)).all()
        other = s.scalars(select(TranscriptChunk.id).where(TranscriptChunk.video_id == vb)).first()

    fake_llm.responders["notes"] = lambda prompt: {
        "summary": "Bài về gradient descent.",
        "topics": [{"title": "Learning rate", "points": [
            {"text": "Learning rate lớn gây dao động", "refs": [f"C{c_ids[1]}"]},
            {"text": "Ý bịa", "refs": ["C999999"]},                  # id does not exist
            {"text": "Ý của video khác", "refs": [f"C{other}"]},       # exists, but not in this video
        ]}],
    }
    note = generate_notes(svc, va)
    points = note["topics"][0]["points"]
    assert len(points) == 1 and note["dropped_uncited_points"] == 2
    cite = points[0]["citations"][0]
    assert cite["start"] == 40 and cite["url"].endswith("?t=40")
    assert cite["frame_url"] is None  # the only slide appears at 80s, after this passage
    with svc.db.session() as s:
        from app.citations import resolve_refs

        later = resolve_refs(s, [f"C{c_ids[2]}"], {va})[f"C{c_ids[2]}"]  # passage at 85s
    assert later["frame_url"] and later["frame_time"] == 80
    with svc.db.session() as s:
        assert s.scalar(select(func.count()).select_from(Note)) == 1
        stored = json.loads(s.scalars(select(Note)).first().content_json)
        assert stored["summary"] == "Bài về gradient descent."


def test_chat_answer_has_valid_citations_only(svc, fake_llm, series_with_videos):
    sid, va, _ = series_with_videos

    def responder(prompt: str) -> dict:
        import re

        first = re.search(r"\[(C\d+)\]", prompt).group(1)
        return {"answer": f"Learning rate quá lớn làm loss dao động [{first}]. Bịa thêm [C424242].",
                "insufficient_evidence": False}

    fake_llm.responders["chat"] = responder
    with svc.db.session() as s:
        cs = ChatSession(series_id=sid)
        s.add(cs)
        s.flush()
        cs_id = cs.id
    msg = chat.ask(svc, cs_id, "Learning rate quá lớn thì sao?")
    assert "C424242" not in msg["content"]
    assert len(msg["citations"]) == 1 and msg["citations"][0]["youtube_id"] == "AAAAAAAAAAA"
    # the grounding context sent to the model contains the lecture excerpt
    purpose, prompt = fake_llm.calls[-1]
    assert purpose == "chat" and "dao động" in prompt


def test_chat_without_evidence_skips_model(svc, fake_llm):
    with svc.db.session() as s:
        series = Series(title="Rỗng")
        s.add(series)
        s.flush()
        cs = ChatSession(series_id=series.id)
        s.add(cs)
        s.flush()
        cs_id = cs.id
    msg = chat.ask(svc, cs_id, "Định lý Pythagore là gì?")
    assert msg["insufficient_evidence"] is True and msg["citations"] == []
    assert not [c for c in fake_llm.calls if c[0] == "chat"]
