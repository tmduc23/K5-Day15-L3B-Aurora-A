from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.embeddings import HashEmbedder  # noqa: E402
from app.llm import FakeLLM  # noqa: E402
from app.models import Frame, Series, TranscriptChunk, Video  # noqa: E402
from app.services import build_services  # noqa: E402


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(
        data_dir=tmp_path / "data",
        llm_provider="fake",
        embedding_provider="hash",
        worker_enabled=False,
        frame_sample_sec=1.0,
        frame_min_gap_sec=2.0,
    )


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def svc(settings, fake_llm):
    return build_services(settings, llm=fake_llm, embedder=HashEmbedder())


LECTURE_A = [
    (0, 40, "Hôm nay chúng ta học về gradient descent, thuật toán tối ưu cơ bản trong học máy."),
    (40, 85, "Learning rate quá lớn làm loss dao động và không hội tụ. Learning rate quá nhỏ thì hội tụ rất chậm."),
    (85, 130, "Công thức cập nhật là theta bằng theta trừ alpha nhân đạo hàm của hàm mất mát."),
]
LECTURE_B = [
    (0, 45, "Bài này nói về mạng nơ-ron tích chập CNN dùng cho xử lý ảnh."),
    (45, 90, "Lớp pooling giảm kích thước đặc trưng và giúp mô hình bất biến với dịch chuyển nhỏ."),
]


def add_video(svc, series_id: int, youtube_id: str, lines, position: int = 0, frames=()) -> int:
    with svc.db.session() as s:
        v = Video(series_id=series_id, youtube_id=youtube_id, position=position, title=f"Bài {position + 1}",
                  status="COMPLETED", progress=100)
        s.add(v)
        s.flush()
        for i, (a, b, t) in enumerate(lines):
            s.add(TranscriptChunk(video_id=v.id, idx=i, start=a, end_time=b, text=t, language="vi"))
        for i, (t, slide) in enumerate(frames):
            s.add(Frame(video_id=v.id, idx=i, timestamp=t, image_path=f"{youtube_id}/{i}.jpg", image_hash="0" * 64,
                        slide_text=slide, summary="slide", has_content=True))
        s.flush()
        svc.index.index_video(s, v)
        return v.id


@pytest.fixture
def series_with_videos(svc):
    with svc.db.session() as s:
        series = Series(title="Học máy")
        s.add(series)
        s.flush()
        sid = series.id
    va = add_video(svc, sid, "AAAAAAAAAAA", LECTURE_A, 0, frames=[(80, "Learning rate alpha: quá lớn → dao động")])
    vb = add_video(svc, sid, "BBBBBBBBBBB", LECTURE_B, 1)
    return sid, va, vb


def make_slide_video(path: Path, slides: list[int], seconds_each: int = 6, fps: int = 5) -> Path:
    """Synthetic lecture: each slide is a distinct pattern held still for `seconds_each`."""
    w, h = 320, 180
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    assert writer.isOpened()
    for sid in slides:
        img = np.full((h, w, 3), 255, np.uint8)
        rng = np.random.default_rng(sid)
        for _ in range(6):
            x, y = rng.integers(0, w - 60), rng.integers(0, h - 30)
            cv2.rectangle(img, (int(x), int(y)), (int(x) + 60, int(y) + 30), (0, 0, 0), -1)
        cv2.putText(img, f"SLIDE {sid}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (40, 40, 200), 3)
        for _ in range(seconds_each * fps):
            writer.write(img)
    writer.release()
    return path
