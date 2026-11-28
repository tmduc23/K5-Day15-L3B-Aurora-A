"""Hybrid retrieval over transcript chunks and keyframes.

Two retrievers run over the same scope (a series, optionally some videos):
  * dense: cosine similarity on multilingual text embeddings (transcript text, slide text + description)
  * keyword: SQLite FTS5 BM25, diacritics-insensitive, catches exact terms and formula names
Their ranked lists are merged with Reciprocal Rank Fusion, which uses ranks only, so scores from
different scorers never have to be calibrated against each other. Hits are then grouped into time
segments, since one idea in a lecture usually spans neighbouring chunks and the slide shown then.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from .db import Database
from .embeddings import Embedder, from_blob, to_blob
from .models import Frame, TranscriptChunk, Video

log = logging.getLogger(__name__)
RRF_K = 60
WORD_RE = re.compile(r"\w+", re.UNICODE)


@dataclass
class Hit:
    kind: str  # "chunk" | "frame"
    ref_id: int
    video_id: int
    start: float
    end: float
    text: str
    score: float = 0.0
    sources: list[str] = field(default_factory=list)  # which retrievers found it

    @property
    def ref(self) -> str:
        return ("C" if self.kind == "chunk" else "F") + str(self.ref_id)


@dataclass
class TimeSegment:
    video_id: int
    start: float
    end: float
    score: float
    hits: list[Hit]


def frame_text(f: Frame) -> str:
    parts = [p for p in (f.slide_text, f.summary) if p]
    return "\n".join(parts)


class SearchIndex:
    def __init__(self, db: Database, embedder: Embedder):
        self.db = db
        self.embedder = embedder

    # ---- indexing -------------------------------------------------------------------------
    def index_video(self, s: Session, video: Video) -> tuple[int, int]:
        """(Re)build vectors and keyword rows for one video. Idempotent."""
        self.remove_video(s, video.id)
        chunks = list(video.chunks)
        frames = [f for f in video.frames if f.has_content is not False and frame_text(f)]
        texts = [c.text for c in chunks] + [frame_text(f) for f in frames]
        vecs = self.embedder.embed_passages(texts) if texts else []
        for obj, v in zip(chunks + frames, vecs):
            obj.embedding = to_blob(v)
            obj.embedding_model = self.embedder.name
        rows = [
            {"content": c.text, "kind": "chunk", "ref_id": c.id, "video_id": video.id, "series_id": video.series_id}
            for c in chunks
        ] + [
            {"content": frame_text(f), "kind": "frame", "ref_id": f.id, "video_id": video.id,
             "series_id": video.series_id}
            for f in frames
        ]
        if rows:
            s.execute(
                text("INSERT INTO search_fts(content, kind, ref_id, video_id, series_id) "
                     "VALUES (:content, :kind, :ref_id, :video_id, :series_id)"),
                rows,
            )
        return len(chunks), len(frames)

    @staticmethod
    def remove_video(s: Session, video_id: int) -> None:
        s.execute(text("DELETE FROM search_fts WHERE video_id = :v"), {"v": video_id})

    # ---- retrieval ------------------------------------------------------------------------
    def search(
        self,
        series_id: int,
        query: str,
        video_ids: list[int] | None = None,
        top_k: int = 8,
        mode: str = "hybrid",
        pool: int = 30,
    ) -> list[Hit]:
        query = (query or "").strip()
        if not query:
            return []
        with self.db.session() as s:
            dense = self._dense(s, series_id, query, video_ids, pool) if mode in ("hybrid", "dense") else []
            keyword = self._keyword(s, series_id, query, video_ids, pool) if mode in ("hybrid", "keyword") else []
        fused: dict[tuple[str, int], Hit] = {}
        for name, ranked in (("dense", dense), ("keyword", keyword)):
            for rank, h in enumerate(ranked):
                key = (h.kind, h.ref_id)
                cur = fused.setdefault(key, Hit(h.kind, h.ref_id, h.video_id, h.start, h.end, h.text))
                cur.score += 1.0 / (RRF_K + rank + 1)
                cur.sources.append(name)
        return sorted(fused.values(), key=lambda h: h.score, reverse=True)[:top_k]

    def _scope(self, stmt, model, series_id: int, video_ids: list[int] | None):
        stmt = stmt.join(Video, Video.id == model.video_id).where(Video.series_id == series_id)
        if video_ids:
            stmt = stmt.where(model.video_id.in_(video_ids))
        return stmt

    def _dense(self, s: Session, series_id: int, query: str, video_ids, pool: int) -> list[Hit]:
        cand: list[Hit] = []
        vecs: list[np.ndarray] = []
        name = self.embedder.name
        cq = self._scope(
            select(TranscriptChunk.id, TranscriptChunk.video_id, TranscriptChunk.start, TranscriptChunk.end_time,
                   TranscriptChunk.text, TranscriptChunk.embedding)
            .where(TranscriptChunk.embedding.is_not(None), TranscriptChunk.embedding_model == name),
            TranscriptChunk, series_id, video_ids)
        for cid, vid, st, en, txt, emb in s.execute(cq):
            cand.append(Hit("chunk", cid, vid, st, en, txt))
            vecs.append(from_blob(emb))
        fq = self._scope(
            select(Frame).where(Frame.embedding.is_not(None), Frame.embedding_model == name),
            Frame, series_id, video_ids)
        for f in s.scalars(fq):
            cand.append(Hit("frame", f.id, f.video_id, f.timestamp, f.timestamp, frame_text(f)))
            vecs.append(from_blob(f.embedding))
        if not cand:
            return []
        q = self.embedder.embed_query(query)
        sims = np.stack(vecs) @ q
        order = np.argsort(-sims)[:pool]
        out = []
        for i in order:
            if sims[i] <= 0:
                break  # nothing in common with the query
            cand[i].score = float(sims[i])
            out.append(cand[i])
        return out

    def _keyword(self, s: Session, series_id: int, query: str, video_ids, pool: int) -> list[Hit]:
        words = [w for w in WORD_RE.findall(query) if len(w) > 1]
        if not words:
            return []
        match = " OR ".join('"' + w.replace('"', "") + '"' for w in words[:32])
        sql = ("SELECT kind, ref_id, video_id FROM search_fts WHERE search_fts MATCH :m AND series_id = :s "
               "ORDER BY bm25(search_fts) LIMIT :n")
        rows = s.execute(text(sql), {"m": match, "s": series_id, "n": pool * 3}).all()
        allowed = set(video_ids) if video_ids else None
        rows = [r for r in rows if allowed is None or int(r.video_id) in allowed][:pool]
        chunk_ids = [int(r.ref_id) for r in rows if r.kind == "chunk"]
        frame_ids = [int(r.ref_id) for r in rows if r.kind == "frame"]
        chunks = {c.id: c for c in s.scalars(select(TranscriptChunk).where(TranscriptChunk.id.in_(chunk_ids)))}
        frames = {f.id: f for f in s.scalars(select(Frame).where(Frame.id.in_(frame_ids)))}
        out = []
        for r in rows:
            if r.kind == "chunk" and int(r.ref_id) in chunks:
                c = chunks[int(r.ref_id)]
                out.append(Hit("chunk", c.id, c.video_id, c.start, c.end_time, c.text))
            elif r.kind == "frame" and int(r.ref_id) in frames:
                f = frames[int(r.ref_id)]
                out.append(Hit("frame", f.id, f.video_id, f.timestamp, f.timestamp, frame_text(f)))
        return out


def group_segments(hits: list[Hit], window: float = 60.0) -> list[TimeSegment]:
    """Merge hits of the same video that lie within `window` seconds of each other."""
    by_video: dict[int, list[Hit]] = {}
    for h in hits:
        by_video.setdefault(h.video_id, []).append(h)
    segments: list[TimeSegment] = []
    for vid, hs in by_video.items():
        hs.sort(key=lambda h: h.start)
        cur = TimeSegment(vid, hs[0].start, hs[0].end, hs[0].score, [hs[0]])
        for h in hs[1:]:
            if h.start - cur.end <= window:
                cur.end = max(cur.end, h.end)
                cur.score += h.score
                cur.hits.append(h)
            else:
                segments.append(cur)
                cur = TimeSegment(vid, h.start, h.end, h.score, [h])
        segments.append(cur)
    return sorted(segments, key=lambda g: g.score, reverse=True)
