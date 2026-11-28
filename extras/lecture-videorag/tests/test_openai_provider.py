"""OpenAI provider: request shape and response handling, with the HTTP client stubbed out."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.llm import LLMError, OpenAILLM


class StubCompletions:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def make(monkeypatch, content='{"answer": "ok [C1]", "insufficient_evidence": false}',
         finish="stop", refusal=None, model="gpt-5-mini"):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    llm = OpenAILLM(model=model)
    msg = SimpleNamespace(content=content, refusal=refusal)
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg, finish_reason=finish)], model=model,
                           usage=SimpleNamespace(prompt_tokens=120, completion_tokens=30))
    stub = StubCompletions(resp)
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=stub))
    return llm, stub


SCHEMA = {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"],
          "additionalProperties": False}


def test_request_shape_and_parsing(monkeypatch):
    llm, stub = make(monkeypatch)
    res = llm.json(purpose="chat", system="sys", schema=SCHEMA, effort="xhigh", content=[
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "QUJD"}},
        {"type": "text", "text": "Hỏi gì đó"},
    ])
    assert res.data["answer"] == "ok [C1]" and res.input_tokens == 120 and res.output_tokens == 30
    k = stub.kwargs
    assert k["messages"][0] == {"role": "system", "content": "sys"}
    user = k["messages"][1]["content"]
    assert user[0] == {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,QUJD"}}
    assert user[1] == {"type": "text", "text": "Hỏi gì đó"}
    assert k["response_format"]["json_schema"] == {"name": "chat", "schema": SCHEMA, "strict": True}
    assert k["reasoning_effort"] == "high"  # xhigh is mapped to the highest OpenAI level
    assert k["max_completion_tokens"] == 16000


def test_non_reasoning_model_gets_no_effort(monkeypatch):
    llm, stub = make(monkeypatch, model="gpt-4.1-mini")
    llm.json(purpose="chat", system="s", schema=SCHEMA, content=[{"type": "text", "text": "x"}])
    assert "reasoning_effort" not in stub.kwargs


@pytest.mark.parametrize("kw,msg", [
    ({"finish": "length"}, "bị cắt"),
    ({"refusal": "no"}, "từ chối"),
    ({"content": "not json"}, "JSON"),
])
def test_bad_responses_raise(monkeypatch, kw, msg):
    llm, _ = make(monkeypatch, **kw)
    with pytest.raises(LLMError, match=msg):
        llm.json(purpose="chat", system="s", schema=SCHEMA, content=[{"type": "text", "text": "x"}])


def test_openrouter_base_url_and_prefixed_model(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    llm = OpenAILLM(model="openai/gpt-5-mini", base_url="https://openrouter.ai/api/v1")
    assert str(llm.client.base_url).startswith("https://openrouter.ai/api/v1")
    assert llm._reasoning  # vendor prefix is ignored when detecting reasoning models
    assert not OpenAILLM(model="openai/gpt-4o-mini")._reasoning
