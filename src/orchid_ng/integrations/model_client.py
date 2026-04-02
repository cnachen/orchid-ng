from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from litellm import completion
from pydantic import BaseModel

ResponseModelT = TypeVar("ResponseModelT", bound=BaseModel)


class ModelClient:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def generate(
        self, prompt: str, response_model: type[ResponseModelT]
    ) -> ResponseModelT:
        raise NotImplementedError


class LiteLLMModelClient(ModelClient):
    def __init__(self, model_name: str, temperature: float = 0.2) -> None:
        super().__init__(model_name=model_name)
        self.temperature = temperature

    def generate(
        self, prompt: str, response_model: type[ResponseModelT]
    ) -> ResponseModelT:
        schema = json.dumps(
            response_model.model_json_schema(), ensure_ascii=False, indent=2
        )
        response = completion(
            model=self.model_name,
            temperature=self.temperature,
            messages=[
                {
                    "role": "system",
                    "content": "You are a structured assistant. Return JSON only.",
                },
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nReturn a JSON object that matches this schema:\n{schema}"
                    ),
                },
            ],
        )
        content = _normalize_content(response.choices[0].message.content)
        json_payload = _extract_json(content)
        return response_model.model_validate_json(json_payload)


class FakeModelClient(ModelClient):
    def __init__(self, scripted_responses: Iterable[Any]) -> None:
        super().__init__(model_name="fake-model")
        self._responses = list(scripted_responses)
        self.history: list[str] = []

    def generate(
        self, prompt: str, response_model: type[ResponseModelT]
    ) -> ResponseModelT:
        self.history.append(prompt)
        if not self._responses:
            raise RuntimeError("FakeModelClient response queue is empty")
        payload = self._responses.pop(0)
        if isinstance(payload, Callable):
            payload = payload(prompt, response_model)
        if isinstance(payload, response_model):
            return payload
        if isinstance(payload, BaseModel):
            payload = payload.model_dump(mode="json")
        if isinstance(payload, str):
            try:
                return response_model.model_validate_json(payload)
            except Exception:
                payload = json.loads(payload)
        return response_model.model_validate(payload)


def _normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                chunks.append(item.get("text", ""))
        return "\n".join(chunks).strip()
    raise TypeError(f"Unsupported response content: {type(content)!r}")


def _extract_json(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if not match:
        raise ValueError(
            f"Could not locate JSON payload in model response: {content!r}"
        )
    return match.group(0)
