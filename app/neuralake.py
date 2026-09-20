"""NeuraLake client — OpenAI-compatible, capability routing, cost tracking.

model="auto" for the orchestrator; named capabilities (reasoning, reasoning-pro,
code) for the judge panel — cross-capability = real cross-model diversity.
Cross Memory is requested via the `cross_memory` extra field; if the API ignores
it we degrade gracefully (state is still passed explicitly).
"""

import os
from typing import Any

from openai import OpenAI

CAPABILITIES = ("text", "code", "reasoning", "reasoning-pro", "multimodal", "auto")


class NeuraLake:
    def __init__(self, api_key: str | None = None, base_url: str | None = None,
                 db: Any = None):
        self.client = OpenAI(
            base_url=base_url or os.environ.get(
                "NEURALAKE_BASE_URL", "https://api.neuralake.cloud/v1"),
            api_key=api_key or os.environ["NEURALAKE_API_KEY"],
        )
        self.total_cost = 0.0
        self.calls: list[dict] = []
        self.db = db   # optional: persist each call so cost survives restarts

    def complete(self, messages: list[dict], model: str = "auto",
                 max_tokens: int = 2048, temperature: float = 0.2,
                 extra: dict[str, Any] | None = None) -> dict:
        assert model in CAPABILITIES, f"unknown capability {model}"
        kwargs: dict[str, Any] = {}
        if extra:
            kwargs["extra_body"] = extra
        from openai import APIConnectionError, APIError, APITimeoutError
        from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3),
               wait=wait_exponential(multiplier=1, min=2, max=20),
               retry=retry_if_exception_type(
                   (APIError, APITimeoutError, APIConnectionError)),
               reraise=True)
        def _call():
            return self.client.chat.completions.create(
                model=model, messages=messages, max_tokens=max_tokens,
                temperature=temperature, timeout=120, **kwargs)

        r = _call()
        cost = getattr(r.usage, "estimated_cost", None) or 0.0
        self.total_cost += cost
        call = {"model_requested": model, "model_used": getattr(r, "model", model),
                "prompt_tokens": r.usage.prompt_tokens,
                "completion_tokens": r.usage.completion_tokens, "cost": cost}
        self.calls.append(call)
        if self.db is not None:
            self.db.execute(
                "INSERT INTO inference_calls"
                "(ts,model_requested,model_used,prompt_tokens,"
                "completion_tokens,cost) VALUES(?,?,?,?,?,?)",
                (self.db.now(), call["model_requested"], call["model_used"],
                 call["prompt_tokens"], call["completion_tokens"], call["cost"]))
        return {"content": r.choices[0].message.content, **call}
