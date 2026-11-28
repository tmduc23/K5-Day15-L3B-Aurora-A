"""Application settings, read from environment variables (prefix LVR_) and an optional .env file."""
from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path = ROOT / ".env") -> None:
    """Load KEY=VALUE lines into os.environ without overriding existing variables.

    Needed so non-prefixed variables such as ANTHROPIC_API_KEY reach the Anthropic SDK.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LVR_", extra="ignore")

    data_dir: Path = ROOT / "data"
    database_url: str | None = None  # default: sqlite file inside data_dir

    llm_provider: str = "openai"  # openai | anthropic | fake
    llm_model: str = "claude-opus-5-5"  # used when llm_provider=anthropic
    openai_model: str = "gpt-5-mini"  # used when llm_provider=openai
    openai_base_url: str | None = None  # e.g. https://openrouter.ai/api/v1 for OpenRouter
    llm_fallbacks: bool = True
    effort_frames: str = "low"
    effort_notes: str = "high"
    effort_chat: str = "medium"
    llm_concurrency: int = 4

    embedding_provider: str = "sentence-transformers"  # sentence-transformers | hash
    embedding_model: str = "intfloat/multilingual-e5-small"

    output_language: str = "vi"  # vi | en | auto
    transcript_languages: list[str] = ["vi", "en"]
    chunk_target_sec: float = 45.0
    chunk_max_sec: float = 75.0

    describe_frames: bool = True
    frame_sample_sec: float = 2.0
    frame_diff_threshold: float = 8.0
    frame_min_gap_sec: float = 4.0
    max_frames_per_video: int = 60
    video_max_height: int = 720
    keep_video_files: bool = False
    # Where the transcript comes from:
    #   auto      = YouTube subtitles if present, otherwise Whisper speech-to-text
    #   whisper   = always Whisper (LMS-style videos without subtitles; also to demo that path on YouTube)
    #   subtitles = YouTube subtitles only, fail when there are none
    transcript_mode: str = "auto"
    whisper_model: str = "large-v3-turbo"  # ~1.5 GB, ~12x real time on a 4 GB GPU; "small" for CPU-only machines
    whisper_language: str = ""  # "" = auto-detect; "vi" / "en" to force
    # LMS videos (uploaded files / direct download links) are kept in uploads_dir for in-app playback
    max_upload_mb: int = 4096
    download_timeout_sec: float = 60.0

    worker_enabled: bool = True
    search_top_k: int = 8
    chat_context_segments: int = 6

    @property
    def db_url(self) -> str:
        return self.database_url or f"sqlite:///{(self.data_dir / 'videorag.db').as_posix()}"

    @property
    def frames_dir(self) -> Path:
        return self.data_dir / "frames"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "videos"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.frames_dir, self.media_dir, self.uploads_dir):
            d.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    load_dotenv()
    return Settings()
