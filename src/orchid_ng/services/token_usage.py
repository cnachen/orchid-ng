from orchid_ng.utils.singleton import SingletonMeta
from orchid_ng.services.config import ConfigService
from orchid_ng.utils.fs import ensure_file
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


@dataclass(frozen=True, slots=True)
class TokenUsageRecord:
    ts: str
    tag: str
    group: str | None
    model: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    meta: dict[str, Any] | None


class TokenUsageService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.path: Path = ConfigService().current_run_dir / "token_usage.jsonl"
        ensure_file(self.path)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    @staticmethod
    def _coerce_int(value: Any) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, str):
            v = value.strip()
            if v.isdigit():
                return int(v)
        return None

    @staticmethod
    def _extract_usage_from_response(response: Any) -> dict[str, Any] | None:
        if response is None:
            return None
        if isinstance(response, dict):
            usage = response.get("usage")
            return usage if isinstance(usage, dict) else None
        usage = getattr(response, "usage", None)
        if isinstance(usage, dict):
            return usage
        try:
            usage_dict = usage.model_dump()
            return usage_dict if isinstance(usage_dict, dict) else None
        except Exception:
            return None

    @staticmethod
    def _extract_model_from_response(response: Any) -> str | None:
        if response is None:
            return None
        if isinstance(response, dict):
            model = response.get("model")
            return model if isinstance(model, str) and model.strip() else None
        model = getattr(response, "model", None)
        return model if isinstance(model, str) and model.strip() else None

    def append_record(self, record: TokenUsageRecord) -> None:
        payload = {
            "ts": record.ts,
            "tag": record.tag,
            "group": record.group,
            "model": record.model,
            "prompt_tokens": record.prompt_tokens,
            "completion_tokens": record.completion_tokens,
            "total_tokens": record.total_tokens,
            "meta": record.meta,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def append(
        self,
        *,
        tag: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        model: str | None = None,
        group: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        if tag.strip() == "":
            raise ValueError("tag must not be empty")
        self.append_record(
            TokenUsageRecord(
                ts=self._now_iso(),
                tag=tag,
                group=group,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                meta=meta,
            )
        )

    def append_from_litellm(
        self,
        *,
        tag: str,
        response: Any,
        group: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        usage = self._extract_usage_from_response(response) or {}
        prompt_tokens = self._coerce_int(usage.get("prompt_tokens"))
        completion_tokens = self._coerce_int(usage.get("completion_tokens"))
        total_tokens = self._coerce_int(usage.get("total_tokens"))
        model = self._extract_model_from_response(response)
        self.append(
            tag=tag,
            group=group,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            meta=meta,
        )
