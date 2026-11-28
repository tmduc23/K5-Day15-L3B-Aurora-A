"""Smoke test against real YouTube (no Claude calls): subtitles, download, keyframes, embeddings.

Usage: python scripts/smoke_youtube.py <youtube url> [--no-video]
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import frames, transcript, youtube  # noqa: E402
from app.citations import fmt_time  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.embeddings import build_embedder  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("url")
    p.add_argument("--no-video", action="store_true")
    args = p.parse_args()
    st = get_settings()

    t0 = time.time()
    title, vids = youtube.expand(args.url)
    print(f"[expand] {title!r}: {len(vids)} video(s) in {time.time() - t0:.1f}s")
    vid = vids[0].youtube_id

    t0 = time.time()
    meta = youtube.fetch_metadata(vid)
    print(f"[metadata] {meta.title!r} by {meta.channel}, {meta.duration}s ({time.time() - t0:.1f}s)")

    t0 = time.time()
    segs, lang, source = youtube.fetch_subtitles(vid, st.transcript_languages)
    chunks = transcript.chunk_segments(segs, st.chunk_target_sec, st.chunk_max_sec)
    print(f"[subtitles] {len(segs)} lines, lang={lang}, source={source} -> {len(chunks)} chunks "
          f"({time.time() - t0:.1f}s)")
    for c in chunks[:2]:
        print(f"   {fmt_time(c.start)}-{fmt_time(c.end)} {c.text[:110]}")

    t0 = time.time()
    emb = build_embedder(st.embedding_provider, st.embedding_model)
    vecs = emb.embed_passages([c.text for c in chunks])
    q = emb.embed_query("what is a neuron in a neural network")
    best = int((vecs @ q).argmax())
    print(f"[embed] {emb.name}: {vecs.shape} in {time.time() - t0:.1f}s; "
          f"best chunk for test query at {fmt_time(chunks[best].start)}: {chunks[best].text[:90]}")

    if args.no_video:
        return
    with tempfile.TemporaryDirectory() as tmp:
        t0 = time.time()
        path = youtube.download_video(vid, Path(tmp), st.video_max_height)
        size = path.stat().st_size / 1e6
        print(f"[download] {path.name} {size:.1f} MB in {time.time() - t0:.1f}s")
        t0 = time.time()
        kfs = frames.extract_keyframes(path, st.frame_sample_sec, st.frame_diff_threshold, st.frame_min_gap_sec,
                                       st.max_frames_per_video)
        print(f"[keyframes] {len(kfs)} in {time.time() - t0:.1f}s at: "
              + ", ".join(fmt_time(k.timestamp) for k in kfs[:20]) + (" ..." if len(kfs) > 20 else ""))
        out = Path(__file__).resolve().parent.parent / "data" / "smoke" / vid
        for k in kfs[:6]:
            frames.save_jpeg(k.image, out / f"{int(k.timestamp):05d}.jpg")
        print(f"[saved] first frames in {out}")


if __name__ == "__main__":
    main()
