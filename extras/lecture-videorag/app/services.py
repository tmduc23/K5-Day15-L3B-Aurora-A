"""Service container: one place that wires settings, database, LLM, embedder and search index."""
from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .db import Database
from .embeddings import Embedder, build_embedder
from .llm import LLM, LLMResult, build_llm
from .models import LlmCall
from .search import SearchIndex


@dataclass
class Services:
    settings: Settings
    db: Database
    llm: LLM
    embedder: Embedder
    index: SearchIndex

    def call_llm(self, *, purpose: str, video_id: int | None = None, **kwargs) -> LLMResult:
        res = self.llm.json(purpose=purpose, **kwargs)
        with self.db.session() as s:
            s.add(LlmCall(purpose=purpose, model=res.model, input_tokens=res.input_tokens,
                          output_tokens=res.output_tokens, video_id=video_id))
        return res

    def language_instruction(self, sample: str = "") -> str:
        lang = self.settings.output_language
        if lang == "vi":
            return "Viết toàn bộ bằng tiếng Việt (giữ nguyên thuật ngữ chuyên ngành tiếng Anh khi cần)."
        if lang == "en":
            return "Write everything in English."
        return "Write in the same language as the user's question (or the lecture, if there is no question)."


def build_services(settings: Settings, llm: LLM | None = None, embedder: Embedder | None = None) -> Services:
    settings.ensure_dirs()
    db = Database(settings.db_url)
    db.create_all()
    llm = llm or build_llm(settings.llm_provider, settings.llm_model, settings.llm_fallbacks,
                           settings.openai_model, settings.openai_base_url)
    embedder = embedder or build_embedder(settings.embedding_provider, settings.embedding_model)
    return Services(settings, db, llm, embedder, SearchIndex(db, embedder))
