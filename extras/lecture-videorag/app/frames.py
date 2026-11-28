"""Keyframe extraction: keep one frame per visual change (new slide / new board content).

Every frame is not equally informative. A lecture is mostly long stretches of the same slide, so
we sample at a fixed step, open a new keyframe only when the picture changed enough and has been
stable for a moment, and drop near-duplicates (a slide shown twice) with a perceptual hash.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class KeyFrame:
    timestamp: float
    image: np.ndarray  # BGR
    dhash: str
    change: float  # how different it was from the previous keyframe


def _small_gray(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return cv2.resize(gray, (64, 36), interpolation=cv2.INTER_AREA).astype(np.float32)


def dhash(img: np.ndarray, size: int = 8) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    small = cv2.resize(gray, (size + 1, size), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return "".join("1" if b else "0" for b in bits)


def hamming(a: str, b: str) -> int:
    return sum(x != y for x, y in zip(a, b))


def extract_keyframes(
    video_path: Path,
    sample_sec: float = 2.0,
    diff_threshold: float = 8.0,
    min_gap_sec: float = 4.0,
    max_frames: int = 60,
    dup_hamming: int = 5,
) -> list[KeyFrame]:
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV không mở được video {video_path.name}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, int(round(fps * sample_sec)))

    keyframes: list[KeyFrame] = []
    last_key: np.ndarray | None = None
    last_key_t = -1e9
    pending: tuple[float, np.ndarray, np.ndarray, float] | None = None  # (t, img, small, change)
    idx = 0
    try:
        while True:
            if not cap.grab():  # grab() skips decoding: fast seeking through the stream
                break
            if idx % step:
                idx += 1
                continue
            ok, img = cap.retrieve()
            t = idx / fps
            idx += 1
            if not ok or img is None:
                continue
            small = _small_gray(img)
            if last_key is None:
                _add(keyframes, t, img, 255.0, dup_hamming)
                last_key, last_key_t = small, t
                continue
            change = float(np.mean(np.abs(small - last_key)))
            if pending is not None:
                # Accept the pending change only once the picture has settled (avoids mid-transition frames).
                settled = float(np.mean(np.abs(small - pending[2]))) < diff_threshold / 2
                if settled and pending[0] - last_key_t >= min_gap_sec:
                    _add(keyframes, pending[0], pending[1], pending[3], dup_hamming)
                    last_key, last_key_t = pending[2], pending[0]
                    pending = None
                    continue
                if not settled:
                    pending = (t, img, small, change)
                    continue
            if change >= diff_threshold:
                pending = (t, img, small, change)
        if pending is not None and pending[0] - last_key_t >= min_gap_sec:
            _add(keyframes, pending[0], pending[1], pending[3], dup_hamming)
    finally:
        cap.release()

    if len(keyframes) > max_frames:
        # Keep the strongest visual changes (always keep the first frame), then restore time order.
        first, rest = keyframes[0], sorted(keyframes[1:], key=lambda k: k.change, reverse=True)
        keyframes = sorted([first] + rest[: max_frames - 1], key=lambda k: k.timestamp)
    return keyframes


def _add(keyframes: list[KeyFrame], t: float, img: np.ndarray, change: float, dup_hamming: int) -> None:
    h = dhash(img)
    if any(hamming(h, k.dhash) <= dup_hamming for k in keyframes):
        return  # same slide shown again
    keyframes.append(KeyFrame(t, img, h, change))


def save_jpeg(img: np.ndarray, path: Path, max_width: int = 1280, quality: int = 85) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    h, w = img.shape[:2]
    if w > max_width:
        img = cv2.resize(img, (max_width, int(h * max_width / w)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise RuntimeError("Không mã hoá được JPEG")
    path.write_bytes(buf.tobytes())  # cv2.imwrite fails on non-ASCII Windows paths
