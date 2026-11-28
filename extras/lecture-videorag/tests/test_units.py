from __future__ import annotations

import pytest

from app.citations import fmt_time, refs_in_text, strip_invalid_inline_refs
from app.frames import extract_keyframes
from app.transcript import chunk_segments, clean_text
from app.youtube import InvalidYouTubeUrl, Segment, parse_youtube_url, watch_url

from .conftest import make_slide_video


@pytest.mark.parametrize("url,kind,id_", [
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
    ("youtube.com/watch?v=dQw4w9WgXcQ&t=42s", "video", "dQw4w9WgXcQ"),
    ("https://youtu.be/dQw4w9WgXcQ?si=abc", "video", "dQw4w9WgXcQ"),
    ("https://m.youtube.com/shorts/dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
    ("dQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU", "playlist",
     "PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU", "playlist",
     "PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU"),
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=RDdQw4w9WgXcQ", "video", "dQw4w9WgXcQ"),
])
def test_parse_valid_urls(url, kind, id_):
    p = parse_youtube_url(url)
    assert (p.kind, p.id) == (kind, id_)


@pytest.mark.parametrize("url", [
    "", "https://evil.com/watch?v=dQw4w9WgXcQ", "https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=short", "file:///etc/passwd", "javascript:alert(1)",
    "http://169.254.169.254/latest", "https://www.youtube.com/channel/UC123",
])
def test_parse_rejects_bad_urls(url):
    with pytest.raises(InvalidYouTubeUrl):
        parse_youtube_url(url)


def test_watch_url_has_seconds():
    assert watch_url("dQw4w9WgXcQ", 754.9) == "https://youtu.be/dQw4w9WgXcQ?t=754"


def test_fmt_time():
    assert fmt_time(5) == "00:05"
    assert fmt_time(754) == "12:34"
    assert fmt_time(3725) == "1:02:05"


def test_clean_text_removes_noise():
    assert clean_text("[Music] hello&#39;s\nworld  [Âm nhạc]") == "hello's world"


def test_chunk_closes_at_sentence_after_target():
    segs = [Segment(i * 10, i * 10 + 10, f"câu {i}" + ("." if i in (4, 9) else "")) for i in range(10)]
    chunks = chunk_segments(segs, target_sec=45, max_sec=75)
    assert [(c.start, c.end) for c in chunks] == [(0, 50), (50, 100)]


def test_chunk_hard_cut_without_punctuation():
    segs = [Segment(i * 10, i * 10 + 10, f"từ {i}") for i in range(20)]
    chunks = chunk_segments(segs, target_sec=45, max_sec=75)
    assert all(c.end - c.start <= 80 for c in chunks)
    assert chunks[0].start == 0 and chunks[-1].end == 200
    # every subtitle line lands in exactly one chunk
    assert " ".join(c.text for c in chunks).split() == " ".join(f"từ {i}" for i in range(20)).split()


def test_chunk_folds_tiny_tail():
    segs = [Segment(0, 50, "một đoạn dài."), Segment(50, 55, "đuôi")]
    chunks = chunk_segments(segs, target_sec=45, max_sec=75)
    assert len(chunks) == 1 and chunks[0].end == 55 and chunks[0].text.endswith("đuôi")


def test_keyframes_one_per_slide_and_duplicates_dropped(tmp_path):
    video = make_slide_video(tmp_path / "v.mp4", [1, 2, 3, 1], seconds_each=6)
    kfs = extract_keyframes(video, sample_sec=1.0, diff_threshold=8.0, min_gap_sec=2.0)
    times = [round(k.timestamp) for k in kfs]
    assert len(kfs) == 3, times  # slide 1 shown again at the end is a duplicate
    assert times[0] == 0
    assert 6 <= times[1] <= 8 and 12 <= times[2] <= 14


def test_keyframes_respect_max(tmp_path):
    video = make_slide_video(tmp_path / "v.mp4", list(range(1, 9)), seconds_each=4)
    kfs = extract_keyframes(video, sample_sec=1.0, min_gap_sec=2.0, max_frames=4)
    assert len(kfs) == 4
    assert kfs[0].timestamp == 0
    assert [k.timestamp for k in kfs] == sorted(k.timestamp for k in kfs)


def test_inline_refs():
    text = "Ý A [C1]. Ý B [C2, F9]. Bịa [C404]."
    assert refs_in_text(text) == ["C1", "C2", "F9", "C404"]
    cleaned = strip_invalid_inline_refs(text, {"C1", "F9"})
    assert cleaned == "Ý A [C1]. Ý B [F9]. Bịa."
