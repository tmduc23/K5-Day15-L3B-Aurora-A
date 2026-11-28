"""In-process background worker (replaces Celery + Redis).

Jobs live in the SQLite `jobs` table, so they survive restarts: on start, any job left RUNNING by a
crash goes back to PENDING. One worker thread processes one video at a time, which suits a single
GPU and SQLite's single writer.
"""
from __future__ import annotations

import logging
import threading
import traceback

from sqlalchemy import select, update

from .models import Job, Video, utcnow
from .pipeline import process_video
from .services import Services

log = logging.getLogger(__name__)


class Worker(threading.Thread):
    def __init__(self, svc: Services, poll_sec: float = 1.0):
        super().__init__(name="video-worker", daemon=True)
        self.svc = svc
        self.poll_sec = poll_sec
        self._stop_event = threading.Event()

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        recover(self.svc)
        while not self._stop_event.is_set():
            try:
                worked = run_next_job(self.svc)
            except Exception:
                log.exception("worker loop error")
                worked = False
            if not worked:
                self._stop_event.wait(self.poll_sec)


def recover(svc: Services) -> None:
    with svc.db.session() as s:
        s.execute(update(Job).where(Job.status == "RUNNING").values(status="PENDING"))


def run_next_job(svc: Services) -> bool:
    """Claim and run the oldest pending job. Returns False when the queue is empty."""
    with svc.db.session() as s:
        job = s.scalars(select(Job).where(Job.status == "PENDING").order_by(Job.id).limit(1)).first()
        if job is None:
            return False
        claimed = s.execute(
            update(Job).where(Job.id == job.id, Job.status == "PENDING")
            .values(status="RUNNING", attempts=Job.attempts + 1, started_at=utcnow())
        ).rowcount
        job_id, video_id = job.id, job.video_id
    if not claimed:
        return True
    try:
        process_video(svc, video_id)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        log.error("job %s failed: %s\n%s", job_id, msg, traceback.format_exc())
        with svc.db.session() as s:
            j = s.get(Job, job_id)
            j.status, j.error_message, j.finished_at = "FAILED", msg, utcnow()
            v = s.get(Video, video_id)
            if v is not None:
                v.status, v.error_message = "FAILED", str(e)
        return True
    with svc.db.session() as s:
        j = s.get(Job, job_id)
        j.status, j.finished_at = "DONE", utcnow()
    return True
