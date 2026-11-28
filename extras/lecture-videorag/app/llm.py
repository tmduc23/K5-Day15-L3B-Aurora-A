"""LLM providers. Every call asks for JSON that matches a schema (structured outputs).

`AnthropicLLM` calls Claude. `FakeLLM` returns canned answers so tests and offline demos
never make paid API calls.
"""
from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    data: dict[str, Any]
    model: str
    input_tokens: int
    output_tokens: int


class LLM(Protocol):
    model: str

    def json(
        self,
        *,
        purpose: str,
        system: str,
        content: list[dict[str, Any]],
        schema: dict[str, Any],
        effort: str = "medium",
        max_tokens: int = 16000,
    ) -> LLMResult: ...


class AnthropicLLM:
    def __init__(self, model: str = "claude-opus-5-5", fallbacks: bool = True):
        import anthropic

        self._anthropic = anthropic
        self.client = anthropic.Anthropic()
        self.model = model
        self.fallbacks = fallbacks

    def json(self, *, purpose, system, content, schema, effort="medium", max_tokens=16000) -> LLMResult:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": effort, "format": {"type": "json_schema", "schema": schema}},
        )
        try:
            if self.fallbacks:
                # Server-side refusal fallback: if a safety classifier declines, the API re-runs
                # the request on a fallback model inside the same call.
                resp = self.client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs
                )
            else:
                resp = self.client.messages.create(**kwargs)
        except self._anthropic.AuthenticationError as e:
            raise LLMError("Sai hoặc thiếu ANTHROPIC_API_KEY") from e
        except self._anthropic.RateLimitError as e:
            raise LLMError("Bị giới hạn tốc độ gọi API, thử lại sau") from e
        except self._anthropic.APIStatusError as e:
            raise LLMError(f"Lỗi API {e.status_code}: {e.message}") from e
        except self._anthropic.APIConnectionError as e:
            raise LLMError("Không kết nối được tới Claude API") from e

        if resp.stop_reason == "refusal":
            raise LLMError("Model từ chối yêu cầu")
        if resp.stop_reason == "max_tokens":
            raise LLMError(f"Câu trả lời bị cắt ở max_tokens={max_tokens} ({purpose})")
        text = next((b.text for b in resp.content if b.type == "text"), None)
        if text is None:
            raise LLMError("Model không trả về nội dung")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON không hợp lệ từ model ({purpose})") from e
        return LLMResult(data, resp.model, resp.usage.input_tokens, resp.usage.output_tokens)


class OpenAILLM:
    """OpenAI Chat Completions with strict JSON-schema output. Reads OPENAI_API_KEY."""

    def __init__(self, model: str = "gpt-5-mini", base_url: str | None = None):
        import openai

        self._openai = openai
        # base_url lets the same client talk to OpenAI-compatible gateways such as OpenRouter.
        self.client = openai.OpenAI(base_url=base_url) if base_url else openai.OpenAI()
        self.model = model
        bare = model.split("/", 1)[-1]  # OpenRouter ids look like "openai/gpt-4o-mini"
        self._reasoning = bare.startswith(("gpt-5", "o1", "o3", "o4"))

    @staticmethod
    def _convert(content: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for b in content:
            if b.get("type") == "image":
                src = b["source"]
                out.append({"type": "image_url",
                            "image_url": {"url": f"data:{src['media_type']};base64,{src['data']}"}})
            else:
                out.append({"type": "text", "text": b.get("text", "")})
        return out

    def json(self, *, purpose, system, content, schema, effort="medium", max_tokens=16000) -> LLMResult:
        kwargs: dict[str, Any] = dict(
            model=self.model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": self._convert(content)}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": purpose, "schema": schema, "strict": True}},
            max_completion_tokens=max_tokens,
        )
        if self._reasoning:
            kwargs["reasoning_effort"] = {"xhigh": "high", "max": "high"}.get(effort, effort)
        oa = self._openai
        try:
            resp = self.client.chat.completions.create(**kwargs)
        except oa.AuthenticationError as e:
            raise LLMError("Sai hoặc thiếu OPENAI_API_KEY") from e
        except oa.RateLimitError as e:
            raise LLMError("Bị giới hạn tốc độ / hết hạn mức OpenAI, thử lại sau") from e
        except oa.APIStatusError as e:
            raise LLMError(f"Lỗi OpenAI API {e.status_code}: {e.message}") from e
        except oa.APIConnectionError as e:
            raise LLMError("Không kết nối được tới OpenAI API") from e

        choice = resp.choices[0]
        if getattr(choice.message, "refusal", None):
            raise LLMError("Model từ chối yêu cầu")
        if choice.finish_reason == "length":
            raise LLMError(f"Câu trả lời bị cắt ở max_tokens={max_tokens} ({purpose})")
        try:
            data = json.loads(choice.message.content or "")
        except json.JSONDecodeError as e:
            raise LLMError(f"JSON không hợp lệ từ model ({purpose})") from e
        usage = resp.usage
        return LLMResult(data, resp.model, usage.prompt_tokens if usage else 0,
                         usage.completion_tokens if usage else 0)


REF_RE = re.compile(r"\[([CF]\d+)\]")


class FakeLLM:
    """Deterministic offline stand-in. Responses cite the first ids found in the prompt."""

    model = "fake"

    def __init__(self, responders: dict[str, Callable[[str], dict]] | None = None):
        self.responders = responders or {}
        self.calls: list[tuple[str, str]] = []

    def json(self, *, purpose, system, content, schema, effort="medium", max_tokens=16000) -> LLMResult:
        prompt = "\n".join(b.get("text", "") for b in content if b.get("type") == "text")
        self.calls.append((purpose, prompt))
        if purpose in self.responders:
            data = self.responders[purpose](prompt)
        else:
            data = self._default(purpose, prompt)
        return LLMResult(data, self.model, 0, 0)

    @staticmethod
    def _default(purpose: str, prompt: str) -> dict:
        refs = REF_RE.findall(prompt)
        if purpose == "frame":
            return {"has_content": True, "slide_text": "", "summary": "Khung hình bài giảng (chế độ giả)"}
        if purpose == "notes":
            chunk_refs = [r for r in refs if r.startswith("C")]
            points = [
                {"text": f"Ý chính số {i + 1} (chế độ giả)", "refs": [r]} for i, r in enumerate(chunk_refs[:3])
            ]
            return {"summary": "Tóm tắt giả — chưa nối model thật.", "topics": [{"title": "Chủ đề", "points": points}]}
        if purpose == "chat":
            if not refs:
                return {"answer": "Không tìm thấy căn cứ trong bài giảng.", "insufficient_evidence": True}
            return {"answer": f"Câu trả lời giả dựa trên [{refs[0]}].", "insufficient_evidence": False}
        return {}


def build_llm(provider: str, model: str, fallbacks: bool, openai_model: str = "gpt-5-mini",
              openai_base_url: str | None = None) -> LLM:
    if provider == "fake":
        return FakeLLM()
    if provider == "openai":
        return OpenAILLM(model=openai_model, base_url=openai_base_url or None)
    if provider == "anthropic":
        return AnthropicLLM(model=model, fallbacks=fallbacks)
    raise ValueError(f"LLM provider không hỗ trợ: {provider}")
