from orchid_ng.utils.singleton import SingletonMeta
import os
import re
from dataclasses import dataclass
from typing import Any

import litellm


@dataclass(frozen=True, slots=True)
class LLMGroupConfig:
    name: str
    models: tuple[str, ...]
    openai_api_key: str | None
    openai_base_url: str | None


class LLMService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self._groups: dict[str, LLMGroupConfig] = {}
        self.reload_from_env()

    @staticmethod
    def _env_get_first(*keys: str) -> str | None:
        for key in keys:
            value = os.getenv(key)
            if value is not None and value.strip() != "":
                return value.strip()
        return None

    @staticmethod
    def _parse_csv(value: str | None) -> tuple[str, ...]:
        if value is None:
            return tuple()
        items = [v.strip() for v in value.split(",")]
        return tuple([v for v in items if v != ""])

    @staticmethod
    def _to_env_prefix(group_name: str) -> str:
        upper = group_name.strip().upper()
        return re.sub(r"[^A-Z0-9]+", "_", upper).strip("_")

    def reload_from_env(self) -> None:
        default_prefix = self._to_env_prefix("default")
        group_names = self._parse_csv(os.getenv("LLM_MODEL_GROUPS")) or ("default",)

        default_models_raw = self._env_get_first(
            f"{default_prefix}_LLM_MODELS",
            f"{default_prefix}_MODELS",
            f"{default_prefix}_MODEL",
        )
        default_models = self._parse_csv(default_models_raw)

        default_openai_base_url = self._env_get_first(
            f"{default_prefix}_OPENAI_BASE_URL"
        )
        default_openai_api_key = self._env_get_first(f"{default_prefix}_OPENAI_API_KEY")

        groups: dict[str, LLMGroupConfig] = {}
        for name in group_names:
            normalized_name = name.strip().lower()
            if normalized_name == "":
                continue
            prefix = self._to_env_prefix(normalized_name)

            models_raw = self._env_get_first(
                f"{prefix}_LLM_MODELS",
                f"{prefix}_MODELS",
                f"{prefix}_MODEL",
            )
            models = self._parse_csv(models_raw)
            if normalized_name == "default":
                models = models or default_models

            if len(models) == 0:
                raise ValueError(
                    f"LLM model group '{normalized_name}' has no models configured."
                )

            openai_base_url = (
                self._env_get_first(f"{prefix}_OPENAI_BASE_URL")
                or default_openai_base_url
            )
            openai_api_key = (
                self._env_get_first(f"{prefix}_OPENAI_API_KEY")
                or default_openai_api_key
            )

            groups[normalized_name] = LLMGroupConfig(
                name=normalized_name,
                models=models,
                openai_api_key=openai_api_key,
                openai_base_url=openai_base_url,
            )

        if len(groups) == 0:
            raise ValueError("No valid LLM model groups configured.")

        self._groups = groups

    def list_groups(self) -> tuple[str, ...]:
        return tuple(self._groups.keys())

    def get_group(self, group: str) -> LLMGroupConfig:
        key = group.strip().lower()
        if key not in self._groups:
            raise KeyError(f"Unknown LLM model group: {group}")
        return self._groups[key]

    def chat(
        self, group: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> list[Any]:
        group_config = self.get_group(group)
        results: list[Any] = []

        call_kwargs = dict(kwargs)
        if group_config.openai_base_url is not None:
            call_kwargs["base_url"] = group_config.openai_base_url
        if group_config.openai_api_key is not None:
            call_kwargs["api_key"] = group_config.openai_api_key

        for model in group_config.models:
            results.append(
                litellm.completion(model=model, messages=messages, **call_kwargs)
            )
        return results

    def chat_all_groups(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, list[Any]]:
        return {
            group: self.chat(group=group, messages=messages, **kwargs)
            for group in self.list_groups()
        }

    async def achat(
        self, group: str, messages: list[dict[str, Any]], **kwargs: Any
    ) -> list[Any]:
        import asyncio

        group_config = self.get_group(group)

        call_kwargs = dict(kwargs)
        if group_config.openai_base_url is not None:
            call_kwargs["base_url"] = group_config.openai_base_url
        if group_config.openai_api_key is not None:
            call_kwargs["api_key"] = group_config.openai_api_key

        coros = [
            litellm.acompletion(model=model, messages=messages, **call_kwargs)
            for model in group_config.models
        ]
        results = await asyncio.gather(*coros)
        return list(results)

    async def achat_all_groups(
        self, messages: list[dict[str, Any]], **kwargs: Any
    ) -> dict[str, list[Any]]:
        import asyncio

        groups = list(self.list_groups())
        results = await asyncio.gather(
            *(self.achat(group=group, messages=messages, **kwargs) for group in groups)
        )
        return dict(zip(groups, results, strict=True))
