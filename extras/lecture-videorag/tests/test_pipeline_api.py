"""End-to-end: ingestion -> worker -> pipeline -> API, with YouTube calls replaced by local fakes."""
from __future__ import annotations

from sqlalchemy import func, select, text
from fastapi.testclient import TestClient

from app import pipeline, youtube
from app.main import create_app
from app.models import Frame, Job, TranscriptChunk, Video
from app.worker import recover, run_next_job

from .conftest import make_slide_video

VID1, VID2 = "dQw4w9WgXcQ", "9bZkp7q19f0"


def fake_youtube(monkeypatch, tmp_path, no_subs: set[str] = frozenset()):
    def expand(url):
        p = youtube.parse_youtube_url(url)
        if p.kind == "playlist":
            return "Khoá học máy", [youtube.VideoInfo(VID1, "Bài 1"), youtube.VideoInfo(VID2, "Bài 2")]
        return None, [youtube.VideoInfo(p.id)]

    def subtitles(video_id, languages):
        if video_id in no_subs:
            raise youtube.TranscriptUnavailable("Video không có phụ đề")
        lines = [youtube.Segment(i * 6, i * 6 + 6, f"Phần {i} nói về gradient descent và learning rate.")
                 for i in range(5)]
        return lines, "vi", "youtube-manual"

    def download_video(video_id, out_dir, max_height):
        return make_slide_video(tmp_path / f"{video_id}.mp4", [1, 2, 3], seconds_each=6)

    monkeypatch.setattr(youtube, "expand", expand)
    monkeypatch.setattr(youtube, "fetch_subtitles", subtitles)
    monkeypatch.setattr(youtube, "download_video", download_video)
    monkeypatch.setattr(youtube, "fetch_metadata",
                        lambda vid: youtube.VideoInfo(vid, f"Video {vid}", "Kênh", 30.0, None))
    monkeypatch.setattr(pipeline.transcript_mod, "whisper_available", lambda: False)


def drain(svc):
    while run_next_job(svc):
        pass


def test_pipeline_end_to_end_and_reprocess(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)
    sid = pipeline.create_series(svc, ["https://www.youtube.com/playlist?list=PLabcdefghijklmnop"])
    drain(svc)
    with svc.db.session() as s:
        videos = s.scalars(select(Video).where(Video.series_id == sid).order_by(Video.position)).all()
        assert [v.status for v in videos] == ["COMPLETED", "COMPLETED"]
        assert videos[0].transcript_source == "youtube-manual" and videos[0].note is not None
        vid = videos[0].id
        n_chunks = s.scalar(select(func.count()).where(TranscriptChunk.video_id == vid))
        n_frames = s.scalar(select(func.count()).where(Frame.video_id == vid))
        n_fts = s.execute(text("SELECT count(*) FROM search_fts WHERE video_id=:v"), {"v": vid}).scalar()
    assert n_chunks >= 1 and n_frames == 3 and n_fts == n_chunks + n_frames
    assert (svc.settings.frames_dir / VID1).is_dir()

    # reprocessing replaces data instead of duplicating it
    assert pipeline.enqueue(svc, vid) is True
    assert pipeline.enqueue(svc, vid) is False  # already queued: no duplicate job
    drain(svc)
    with svc.db.session() as s:
        assert s.scalar(select(func.count()).where(TranscriptChunk.video_id == vid)) == n_chunks
        assert s.scalar(select(func.count()).where(Frame.video_id == vid)) == n_frames
        assert s.execute(text("SELECT count(*) FROM search_fts WHERE video_id=:v"), {"v": vid}).scalar() == n_fts


def test_duplicate_urls_in_one_series_are_merged(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)
    sid = pipeline.create_series(svc, [f"https://youtu.be/{VID1}", f"https://www.youtube.com/watch?v={VID1}"])
    with svc.db.session() as s:
        assert s.scalar(select(func.count()).where(Video.series_id == sid)) == 1


def test_video_without_subtitles_fails_cleanly(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path, no_subs={VID1})
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    drain(svc)
    with svc.db.session() as s:
        v = s.scalars(select(Video)).first()
        job = s.scalars(select(Job)).first()
        assert v.status == "FAILED" and "phụ đề" in v.error_message
        assert job.status == "FAILED" and job.attempts == 1


def test_frame_stage_failure_is_not_fatal(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)

    def broken(*a, **k):
        raise RuntimeError("tải video bị chặn")

    monkeypatch.setattr(youtube, "download_video", broken)
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    drain(svc)
    with svc.db.session() as s:
        v = s.scalars(select(Video)).first()
        assert v.status == "COMPLETED" and "tải video bị chặn" in v.warning and v.note is not None


def test_crash_recovery_requeues_running_jobs(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    with svc.db.session() as s:
        s.scalars(select(Job)).first().status = "RUNNING"
    recover(svc)
    with svc.db.session() as s:
        assert s.scalars(select(Job)).first().status == "PENDING"


def test_api_flow(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)
    client = TestClient(create_app(svc, start_worker=False))

    assert client.get("/api/health").json()["status"] == "ok"
    assert client.post("/api/series", json={"urls": ["https://evil.com/x"]}).status_code == 400

    r = client.post("/api/series", json={"urls": ["https://www.youtube.com/playlist?list=PLabcdefghijklmnop"]})
    assert r.status_code == 201
    series = r.json()
    assert series["title"] == "Khoá học máy" and series["video_count"] == 2
    drain(svc)

    sid = series["id"]
    videos = client.get(f"/api/series/{sid}").json()["videos"]
    assert all(v["status"] == "COMPLETED" for v in videos)
    detail = client.get(f"/api/videos/{videos[0]['id']}").json()
    assert detail["notes"]["topics"] and len(detail["frames"]) == 3 and detail["transcript"]
    point = detail["notes"]["topics"][0]["points"][0]
    assert point["citations"][0]["url"].startswith(f"https://youtu.be/{VID1}?t=")
    assert client.get(detail["frames"][0]["url"]).status_code == 200  # frame image is served

    res = client.post(f"/api/series/{sid}/search", json={"query": "learning rate"}).json()
    assert res["results"] and res["segments"]

    sess = client.post(f"/api/series/{sid}/chat/sessions").json()
    msg = client.post(f"/api/chat/sessions/{sess['id']}/messages", json={"question": "Learning rate là gì?"}).json()
    assert msg["role"] == "assistant" and msg["citations"]
    assert len(client.get(f"/api/chat/sessions/{sess['id']}").json()["messages"]) == 2

    assert client.post(f"/api/videos/{videos[0]['id']}/reprocess").json() == {"queued": True}
    stats = client.get("/api/stats").json()
    assert stats["videos"] == 2 and stats["frames"] == 6

    assert client.delete(f"/api/series/{sid}").status_code == 204
    assert client.get(f"/api/series/{sid}").status_code == 404
    with svc.db.session() as s:
        assert s.execute(text("SELECT count(*) FROM search_fts")).scalar() == 0
    assert not (svc.settings.frames_dir / VID1).exists()


def fake_whisper(monkeypatch, tmp_path, calls):
    def download_audio(video_id, out_dir):
        p = tmp_path / f"{video_id}.audio.m4a"
        p.write_bytes(b"fake audio")
        return p

    def transcribe(path, model_size, language=None, on_progress=None):
        calls.append((path.name, model_size, language))
        if on_progress:
            on_progress(0.5)
        return [youtube.Segment(i * 10, i * 10 + 10, f"Câu nói số {i} về learning rate.") for i in range(6)], "vi"

    monkeypatch.setattr(youtube, "download_audio", download_audio)
    monkeypatch.setattr(pipeline.transcript_mod, "whisper_available", lambda: True)
    monkeypatch.setattr(pipeline.transcript_mod, "transcribe_audio", transcribe)


def test_whisper_mode_ignores_subtitles(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path)  # subtitles exist...
    calls = []
    fake_whisper(monkeypatch, tmp_path, calls)
    svc.settings.transcript_mode = "whisper"  # ...but LMS-style processing always transcribes the audio
    svc.settings.whisper_language = "vi"
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    drain(svc)
    with svc.db.session() as s:
        v = s.scalars(select(Video)).first()
        assert v.status == "COMPLETED" and v.transcript_source == "whisper" and v.language == "vi"
    assert calls == [(f"{VID1}.audio.m4a", svc.settings.whisper_model, "vi")]
    assert not (tmp_path / f"{VID1}.audio.m4a").exists()  # temp audio cleaned up


def test_auto_mode_falls_back_to_whisper(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path, no_subs={VID1})
    calls = []
    fake_whisper(monkeypatch, tmp_path, calls)
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    drain(svc)
    with svc.db.session() as s:
        v = s.scalars(select(Video)).first()
        assert v.status == "COMPLETED" and v.transcript_source == "whisper"
    assert len(calls) == 1


def test_subtitles_mode_never_uses_whisper(svc, monkeypatch, tmp_path):
    fake_youtube(monkeypatch, tmp_path, no_subs={VID1})
    calls = []
    fake_whisper(monkeypatch, tmp_path, calls)
    svc.settings.transcript_mode = "subtitles"
    pipeline.create_series(svc, [f"https://youtu.be/{VID1}"])
    drain(svc)
    with svc.db.session() as s:
        assert s.scalars(select(Video)).first().status == "FAILED"
    assert calls == []
