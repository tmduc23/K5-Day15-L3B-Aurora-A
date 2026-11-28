"""Text embedding providers (multilingual: Vietnamese + English).

Vectors are L2-normalised float32, so cosine similarity is a dot product.
"""
from __future__ import annotations

import hashlib
import logging
import re
import threading
import unicodedata
from typing import Protocol

import numpy as np

log = logging.getLogger(__name__)


class Embedder(Protocol):
    name: str

    def embed_passages(self, texts: list[str]) -> np.ndarray: ...

    def embed_query(self, text: str) -> np.ndarray: ...


class SentenceTransformerEmbedder:
    """Loads lazily on first use. E5 models need 'query: ' / 'passage: ' prefixes."""

    def __init__(self, model_name: str):
        self.name = model_name
        self._model = None
        self._lock = threading.Lock()
        self._e5 = "e5" in model_name.lower()

    def _load(self):
        with self._lock:
            if self._model is None:
                from sentence_transformers import SentenceTransformer

                try:
                    import torch

                    device = "cuda" if torch.cuda.is_available() else "cpu"
                except ImportError:
                    device = "cpu"
                log.info("Loading embedding model %s on %s", self.name, device)
                self._model = SentenceTransformer(self.name, device=device)
        return self._model

    def _encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 0), dtype=np.float32)
        model = self._load()
        vecs = model.encode(texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(vecs, dtype=np.float32)

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        return self._encode([("passage: " + t) if self._e5 else t for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._encode([("query: " + text) if self._e5 else text])[0]


def fold(text: str) -> str:
    """Lowercase and strip Vietnamese diacritics (đ -> d) for keyword matching."""
    text = unicodedata.normalize("NFD", text.lower()).replace("đ", "d")
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


TOKEN_RE = re.compile(r"\w+", re.UNICODE)


class HashEmbedder:
    """Bag-of-words hashing embedder. No model download; used in tests and offline demos."""

    def __init__(self, dim: int = 512):
        self.dim = dim
        self.name = f"hash-{dim}"

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        for tok in TOKEN_RE.findall(fold(text)):
            h = int.from_bytes(hashlib.md5(tok.encode()).digest()[:4], "little")
            v[h % self.dim] += 1.0
        n = np.linalg.norm(v)
        return v / n if n else v

    def embed_passages(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return np.stack([self._vec(t) for t in texts])

    def embed_query(self, text: str) -> np.ndarray:
        return self._vec(text)


def build_embedder(provider: str, model: str) -> Embedder:
    if provider == "hash":
        return HashEmbedder()
    if provider == "sentence-transformers":
        return SentenceTransformerEmbedder(model)
    raise ValueError(f"Embedding provider không hỗ trợ: {provider}")


def to_blob(v: np.ndarray) -> bytes:
    return np.asarray(v, dtype=np.float32).tobytes()


def from_blob(b: bytes) -> np.ndarray:
    return np.frombuffer(b, dtype=np.float32)
