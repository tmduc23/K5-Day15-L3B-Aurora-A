"""SQLAlchemy ORM models. SQLite is the single source of truth (metadata, text, vectors, jobs)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


VIDEO_STATUSES = (
    "PENDING",
    "FETCHING_METADATA",
    "FETCHING_TRANSCRIPT",
    "PROCESSING_FRAMES",
    "INDEXING",
    "SUMMARIZING",
    "COMPLETED",
    "FAILED",
)
JOB_STATUSES = ("PENDING", "RUNNING", "DONE", "FAILED")


class Series(Base):
    """A lecture series: one playlist or a list of video links processed together."""

    __tablename__ = "series"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    videos: Mapped[list[Video]] = relationship(
        back_populates="series", cascade="all, delete-orphan", order_by="Video.position"
    )


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (
        UniqueConstraint("series_id", "youtube_id", name="uq_video_series_youtube"),
        CheckConstraint(f"status IN {VIDEO_STATUSES}", name="ck_video_status"),
        CheckConstraint("progress >= 0 AND progress <= 100", name="ck_video_progress"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True)
    # Source key: the YouTube id, or "f" + 12 hex chars for an LMS video file. Also names the frames folder.
    youtube_id: Mapped[str] = mapped_column(String(16), index=True)
    source_type: Mapped[str] = mapped_column(String(16), default="youtube", server_default="youtube")  # youtube|file
    media_path: Mapped[str | None] = mapped_column(Text)  # file videos: path relative to settings.uploads_dir
    source_url: Mapped[str | None] = mapped_column(Text)  # file videos given as a direct download link
    position: Mapped[int] = mapped_column(Integer, default=0)
    title: Mapped[str | None] = mapped_column(String(500))
    channel: Mapped[str | None] = mapped_column(String(300))
    duration: Mapped[float | None] = mapped_column(Float)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))
    transcript_source: Mapped[str | None] = mapped_column(String(32))  # youtube-manual | youtube-auto | whisper
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    warning: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    series: Mapped[Series] = relationship(back_populates="videos")
    chunks: Mapped[list[TranscriptChunk]] = relationship(
        back_populates="video", cascade="all, delete-orphan", order_by="TranscriptChunk.start"
    )
    frames: Mapped[list[Frame]] = relationship(
        back_populates="video", cascade="all, delete-orphan", order_by="Frame.timestamp"
    )
    note: Mapped[Note | None] = relationship(back_populates="video", cascade="all, delete-orphan", uselist=False)
    jobs: Mapped[list[Job]] = relationship(back_populates="video", cascade="all, delete-orphan")

    @property
    def is_file(self) -> bool:
        return self.source_type == "file"

    def link_at(self, t: float = 0) -> str | None:
        """Where a citation points: YouTube at second t, or the stored file with a #t= media fragment."""
        if not self.is_file:
            return f"https://youtu.be/{self.youtube_id}?t={int(t)}"
        if not self.media_path:
            return self.source_url
        return f"/media/videos/{self.media_path}" + (f"#t={int(t)}" if t else "")

    @property
    def url(self) -> str | None:
        if self.is_file:
            return self.link_at(0)
        return f"https://www.youtube.com/watch?v={self.youtube_id}"


class Job(Base):
    """Durable processing job. The in-process worker claims PENDING jobs one at a time."""

    __tablename__ = "jobs"
    __table_args__ = (CheckConstraint(f"status IN {JOB_STATUSES}", name="ck_job_status"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(16), default="PENDING", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    video: Mapped[Video] = relationship(back_populates="jobs")


class TranscriptChunk(Base):
    __tablename__ = "transcript_chunks"
    __table_args__ = (
        CheckConstraint("end_time >= start", name="ck_chunk_time"),
        Index("ix_chunk_video_start", "video_id", "start"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end_time: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(16))
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    embedding_model: Mapped[str | None] = mapped_column(String(200))

    video: Mapped[Video] = relationship(back_populates="chunks")


class Frame(Base):
    """A keyframe taken where the picture changes (new slide, new board content)."""

    __tablename__ = "frames"
    __table_args__ = (Index("ix_frame_video_time", "video_id", "timestamp"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"))
    idx: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[float] = mapped_column(Float)
    image_path: Mapped[str] = mapped_column(Text)  # relative to settings.frames_dir
    image_hash: Mapped[str] = mapped_column(String(32))
    slide_text: Mapped[str | None] = mapped_column(Text)
    summary: Mapped[str | None] = mapped_column(Text)
    has_content: Mapped[bool | None] = mapped_column()
    embedding: Mapped[bytes | None] = mapped_column(LargeBinary)
    embedding_model: Mapped[str | None] = mapped_column(String(200))

    video: Mapped[Video] = relationship(back_populates="frames")


class Note(Base):
    """Generated knowledge notes for one video (JSON: summary + topics + cited points)."""

    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), unique=True)
    content_json: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    video: Mapped[Video] = relationship(back_populates="note")


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300), default="Cuộc trò chuyện mới")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (CheckConstraint("role IN ('user', 'assistant')", name="ck_msg_role"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    citations_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class LlmCall(Base):
    """One row per model call, for cost tracking."""

    __tablename__ = "llm_calls"
    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    video_id: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
