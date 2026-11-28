"""LMS videos: uploaded files and direct links, transcribed with Whisper (faked here) and played in-app."""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text

from app import localvideo, pipeline, youtube
from app.db import Database
from app.main import create_app
from app.models import Frame, Video
from app.worker import run_next_job

from .conftest import make_slide_video


def drain(svc):
    while run_next_job(svc):
        pass


@pytest.fixture
def lms(svc, monkeypatch, tmp_path):
    """Fake Whisper (records the file it was given); the synthetic videos have no audio track."""
    calls = []

    def transcribe(path, model_size, language=None, on_progress=None):
        calls.append(path)
        assert path.exists()
        if on_progress:
            on_progress(0.5)
        return [youtube.Segment(i * 6, i * 6 + 6, f"Phần {i}: gradient descent và learning rate.")
                for i in range(20)], "vi"  # 2 minutes -> several chunks

    monkeypatch.setattr(pipeline.transcript_mod, "transcribe_audio", transcribe)
    monkeypatch.setattr(pipeline.localvideo, "has_audio", lambda p: True)
    # YouTube must never be touched for file videos
    for name in ("fetch_metadata", "fetch_subtitles", "download_video", "download_audio"):
        monkeypatch.setattr(youtube, name, lambda *a, **k: pytest.fail("YouTube called for an LMS video"))
    client = TestClient(create_app(svc, start_worker=False))
    return client, calls


def video_bytes(tmp_path, name="lecture.mp4", slides=(1, 2, 3)) -> bytes:
    return make_slide_video(tmp_path / name, list(slides), seconds_each=6).read_bytes()


def test_upload_process_play_and_delete(svc, lms, tmp_path):
    client, calls = lms
    data = video_bytes(tmp_path)
    files = [("files", ("Bai 10 - CNN.mp4", data, "video/mp4")),
             ("files", ("Bai 2 - Gradient.mp4", data, "video/mp4"))]
    r = client.post("/api/series/upload", files=files, data={"title": "Học máy LMS"})
    assert r.status_code == 201, r.text
    series = r.json()
    assert series["title"] == "Học máy LMS"
    # natural sort: "Bai 2" before "Bai 10"
    assert [v["title"] for v in series["videos"]] == ["Bai 2 - Gradient", "Bai 10 - CNN"]
    assert all(v["source_type"] == "file" and v["duration"] == pytest.approx(18, abs=1) for v in series["videos"])

    drain(svc)
    videos = client.get(f"/api/series/{series['id']}").json()["videos"]
    assert [v["status"] for v in videos] == ["COMPLETED", "COMPLETED"]
    v = client.get(f"/api/videos/{videos[0]['id']}").json()
    assert v["transcript_source"] == "whisper" and len(v["frames"]) == 3
    assert v["thumbnail_url"].startswith("/media/frames/f")
    assert v["media_url"].startswith("/media/videos/f") and v["media_url"].endswith(".mp4")
    assert len(calls) == 2 and all(p.parent == svc.settings.uploads_dir for p in calls)

    # citations point at the stored file with a media fragment, and keep the slide image
    cites = [c for t in v["notes"]["topics"] for p in t["points"] for c in p["citations"]]
    assert cites and all(c["source_type"] == "file" and c["url"].split("#")[0] == v["media_url"] for c in cites)
    hits = client.post(f"/api/series/{series['id']}/search", json={"query": "learning rate"}).json()["results"]
    later = [h for h in hits if h["start"] >= 1]
    assert later and all(h["url"] == f"/media/videos/{h['url'].split('/')[-1].split('#')[0]}#t={int(h['start'])}"
                         for h in later)

    # the player can fetch and seek (HTTP Range)
    assert client.get(v["media_url"]).status_code == 200
    part = client.get(v["media_url"], headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and len(part.content) == 100

    # the file is kept after processing, reprocessing works from it, deleting removes it
    stored = svc.settings.uploads_dir / v["media_url"].rsplit("/", 1)[1]
    assert stored.exists()
    assert client.post(f"/api/videos/{v['id']}/reprocess").json() == {"queued": True}
    drain(svc)
    assert client.get(f"/api/videos/{v['id']}").json()["status"] == "COMPLETED"
    assert client.delete(f"/api/series/{series['id']}").status_code == 204
    assert not stored.exists() and not list(svc.settings.uploads_dir.iterdir())


def test_upload_appends_to_existing_series(svc, lms, tmp_path):
    client, _ = lms
    data = video_bytes(tmp_path)
    sid = client.post("/api/series/upload", files=[("files", ("a.mp4", data, "video/mp4"))]).json()["id"]
    r = client.post("/api/series/upload", files=[("files", ("b.mp4", data, "video/mp4"))], data={"series_id": sid})
    assert r.status_code == 201 and r.json()["id"] == sid
    assert [(v["position"], v["title"]) for v in r.json()["videos"]] == [(0, "a"), (1, "b")]
    assert client.post("/api/series/upload", files=[("files", ("c.mp4", data, "video/mp4"))],
                       data={"series_id": 999}).status_code == 404


def test_upload_rejects_non_video(svc, lms, tmp_path):
    client, _ = lms
    r = client.post("/api/series/upload", files=[("files", ("slides.pdf", b"%PDF-1.4", "application/pdf"))])
    assert r.status_code == 400 and ".mp4" in r.json()["detail"]
    # right extension, not a video: refused, nothing left on disk, no series created
    r = client.post("/api/series/upload", files=[("files", ("fake.mp4", b"not a video at all", "video/mp4"))])
    assert r.status_code == 400 and "fake.mp4" in r.json()["detail"]
    assert not list(svc.settings.uploads_dir.iterdir())
    assert client.get("/api/series").json() == []


def test_video_without_audio_fails_cleanly(svc, monkeypatch, tmp_path):
    client = TestClient(create_app(svc, start_worker=False))
    r = client.post("/api/series/upload", files=[("files", ("silent.mp4", video_bytes(tmp_path), "video/mp4"))])
    drain(svc)  # real has_audio(): the synthetic video has no audio track
    v = client.get(f"/api/series/{r.json()['id']}").json()["videos"][0]
    assert v["status"] == "FAILED" and "âm thanh" in v["error_message"]


def test_direct_link_is_downloaded_by_worker(svc, lms, monkeypatch, tmp_path):
    client, calls = lms
    src = make_slide_video(tmp_path / "src.mp4", [1, 2], seconds_each=6)
    seen = []

    def fake_download(url, out_dir, key, max_bytes, timeout=60.0):
        seen.append(url)
        dest = out_dir / f"{key}.mp4"
        dest.write_bytes(src.read_bytes())
        return dest

    monkeypatch.setattr(pipeline.localvideo, "download_url", fake_download)
    assert client.post("/api/series/links", json={"urls": ["ftp://lms/x.mp4"]}).status_code == 400
    r = client.post("/api/series/links", json={"urls": ["https://lms.example.edu/files/Bai_01.mp4"]})
    assert r.status_code == 201
    v = r.json()["videos"][0]
    assert v["title"] == "Bai 01" and v["status"] == "PENDING" and v["media_url"] is None
    drain(svc)
    v = client.get(f"/api/videos/{v['id']}").json()
    assert seen == ["https://lms.example.edu/files/Bai_01.mp4"]
    assert v["status"] == "COMPLETED" and v["media_url"] and len(v["frames"]) == 2 and v["duration"]


class FakeResponse(io.BytesIO):
    def __init__(self, body: bytes, ctype: str, url: str):
        super().__init__(body)
        self.headers = {"Content-Type": ctype, "Content-Length": str(len(body))}
        self._url = url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


def test_download_url_refuses_login_pages_and_big_files(monkeypatch, tmp_path):
    def serve(body, ctype, url="https://lms.example.edu/video"):
        monkeypatch.setattr(localvideo.urllib.request, "urlopen", lambda req, timeout: FakeResponse(body, ctype, url))

    serve(b"<html>login</html>", "text/html; charset=utf-8")
    with pytest.raises(localvideo.InvalidVideoSource, match="đăng nhập"):
        localvideo.download_url("https://lms.example.edu/video", tmp_path, "fabc", 1 << 20)

    serve(b"x" * 2000, "video/mp4")
    with pytest.raises(localvideo.InvalidVideoSource, match="giới hạn"):
        localvideo.download_url("https://lms.example.edu/video", tmp_path, "fabc", 1000)

    serve(b"x" * 2000, "video/webm")  # no extension in the URL: taken from Content-Type
    p = localvideo.download_url("https://lms.example.edu/video", tmp_path, "fabc", 1 << 20)
    assert p.name == "fabc.webm" and p.stat().st_size == 2000
    assert not list(tmp_path.glob("*.mp4"))  # refused downloads leave nothing behind


def test_helpers():
    assert sorted(["Bai 10.mp4", "Bai 2.mp4", "bai 1.mp4"], key=localvideo.natural_key) == \
        ["bai 1.mp4", "Bai 2.mp4", "Bai 10.mp4"]
    assert localvideo.title_from_filename("Tuan_03__Hoi_quy.mp4") == "Tuan 03 Hoi quy"
    assert localvideo.title_from_url("https://x.edu/a/B%C3%A0i%201.mp4") == "Bài 1"
    with pytest.raises(localvideo.InvalidVideoSource):
        localvideo.check_extension("notes.txt")


def test_old_database_gets_new_columns(tmp_path):
    url = f"sqlite:///{(tmp_path / 'old.db').as_posix()}"
    Database(url).create_all()
    eng = create_engine(url)
    with eng.begin() as c:  # simulate a database made before LMS support
        c.execute(text("INSERT INTO series (title, created_at) VALUES ('s', '2026-01-01')"))
        c.execute(text("INSERT INTO videos (series_id, youtube_id, position, status, progress, created_at, updated_at)"
                       " VALUES (1, 'dQw4w9WgXcQ', 0, 'COMPLETED', 100, '2026-01-01', '2026-01-01')"))
        for col in ("source_type", "media_path", "source_url"):
            c.execute(text(f"ALTER TABLE videos DROP COLUMN {col}"))
    eng.dispose()
    db = Database(url)
    db.create_all()
    with db.session() as s:
        v = s.scalars(select(Video)).one()
        assert v.source_type == "youtube" and v.media_path is None and v.url.startswith("https://www.youtube.com/")
        assert s.scalar(select(func.count()).select_from(Frame)) == 0
