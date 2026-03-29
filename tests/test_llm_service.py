import pytest

from orchid_ng.services.llm import LLMService
from orchid_ng.utils.singleton import SingletonMeta


def _reset_singletons() -> None:
    SingletonMeta._instances.clear()


def test_parse_groups_and_fallback(monkeypatch: pytest.MonkeyPatch):
    _reset_singletons()

    monkeypatch.setenv("LLM_MODEL_GROUPS", "default,reviewers")
    monkeypatch.setenv("DEFAULT_OPENAI_BASE_URL", "https://default.example/v1")
    monkeypatch.setenv("DEFAULT_OPENAI_API_KEY", "default-key")
    monkeypatch.setenv("DEFAULT_LLM_MODELS", "GLM-5")
    monkeypatch.setenv("REVIEWERS_LLM_MODELS", "gpt-5.2,gpt-5.4")
    monkeypatch.delenv("REVIEWERS_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("REVIEWERS_OPENAI_API_KEY", raising=False)

    service = LLMService()

    assert set(service.list_groups()) == {"default", "reviewers"}
    default_group = service.get_group("default")
    reviewers_group = service.get_group("reviewers")

    assert default_group.models == ("GLM-5",)
    assert reviewers_group.models == ("gpt-5.2", "gpt-5.4")

    assert reviewers_group.openai_base_url == default_group.openai_base_url
    assert reviewers_group.openai_api_key == default_group.openai_api_key


def test_group_specific_override(monkeypatch: pytest.MonkeyPatch):
    _reset_singletons()

    monkeypatch.setenv("LLM_MODEL_GROUPS", "default,reviewers")
    monkeypatch.setenv("DEFAULT_OPENAI_BASE_URL", "https://default.example/v1")
    monkeypatch.setenv("DEFAULT_OPENAI_API_KEY", "default-key")
    monkeypatch.setenv("DEFAULT_LLM_MODELS", "GLM-5")
    monkeypatch.setenv("REVIEWERS_LLM_MODELS", "gpt-5.2")
    monkeypatch.setenv("REVIEWERS_OPENAI_BASE_URL", "https://reviewers.example/v1")
    monkeypatch.setenv("REVIEWERS_OPENAI_API_KEY", "reviewers-key")

    service = LLMService()
    reviewers_group = service.get_group("reviewers")

    assert reviewers_group.openai_base_url == "https://reviewers.example/v1"
    assert reviewers_group.openai_api_key == "reviewers-key"


def test_chat_calls_all_models_in_group(monkeypatch: pytest.MonkeyPatch):
    _reset_singletons()

    monkeypatch.setenv("LLM_MODEL_GROUPS", "reviewers")
    monkeypatch.setenv("DEFAULT_OPENAI_BASE_URL", "https://default.example/v1")
    monkeypatch.setenv("DEFAULT_OPENAI_API_KEY", "default-key")
    monkeypatch.setenv("REVIEWERS_LLM_MODELS", "gpt-5.2,gpt-5.4")

    calls: list[dict] = []

    def fake_completion(*, model, messages, **kwargs):
        calls.append({"model": model, "messages": messages, "kwargs": kwargs})
        return {"model": model, "ok": True}

    monkeypatch.setattr("orchid_ng.services.llm.litellm.completion", fake_completion)

    service = LLMService()
    results = service.chat(group="reviewers", messages=[{"role": "user", "content": "hi"}], temperature=0)

    assert [r["model"] for r in results] == ["gpt-5.2", "gpt-5.4"]
    assert [c["model"] for c in calls] == ["gpt-5.2", "gpt-5.4"]
    assert calls[0]["kwargs"]["base_url"] == "https://default.example/v1"
    assert calls[0]["kwargs"]["api_key"] == "default-key"
    assert calls[0]["kwargs"]["temperature"] == 0


@pytest.mark.anyio
async def test_achat_calls_all_models_in_group(monkeypatch: pytest.MonkeyPatch):
    _reset_singletons()

    monkeypatch.setenv("LLM_MODEL_GROUPS", "reviewers")
    monkeypatch.setenv("DEFAULT_OPENAI_BASE_URL", "https://default.example/v1")
    monkeypatch.setenv("DEFAULT_OPENAI_API_KEY", "default-key")
    monkeypatch.setenv("REVIEWERS_LLM_MODELS", "gpt-5.2,gpt-5.4")

    calls: list[dict] = []

    async def fake_acompletion(*, model, messages, **kwargs):
        calls.append({"model": model, "messages": messages, "kwargs": kwargs})
        return {"model": model, "ok": True}

    monkeypatch.setattr("orchid_ng.services.llm.litellm.acompletion", fake_acompletion)

    service = LLMService()
    results = await service.achat(group="reviewers", messages=[{"role": "user", "content": "hi"}], temperature=0)

    assert [r["model"] for r in results] == ["gpt-5.2", "gpt-5.4"]

    calls_by_model = {c["model"]: c for c in calls}
    assert set(calls_by_model.keys()) == {"gpt-5.2", "gpt-5.4"}
    assert calls_by_model["gpt-5.2"]["kwargs"]["base_url"] == "https://default.example/v1"
    assert calls_by_model["gpt-5.2"]["kwargs"]["api_key"] == "default-key"
    assert calls_by_model["gpt-5.2"]["kwargs"]["temperature"] == 0


@pytest.mark.anyio
async def test_achat_all_groups(monkeypatch: pytest.MonkeyPatch):
    _reset_singletons()

    monkeypatch.setenv("LLM_MODEL_GROUPS", "default,reviewers")
    monkeypatch.setenv("DEFAULT_OPENAI_BASE_URL", "https://default.example/v1")
    monkeypatch.setenv("DEFAULT_OPENAI_API_KEY", "default-key")
    monkeypatch.setenv("DEFAULT_LLM_MODELS", "GLM-5")
    monkeypatch.setenv("REVIEWERS_LLM_MODELS", "gpt-5.2")

    async def fake_acompletion(*, model, messages, **kwargs):
        return {"model": model, "ok": True}

    monkeypatch.setattr("orchid_ng.services.llm.litellm.acompletion", fake_acompletion)

    service = LLMService()
    results = await service.achat_all_groups(messages=[{"role": "user", "content": "hi"}], temperature=0)

    assert set(results.keys()) == {"default", "reviewers"}
    assert [r["model"] for r in results["default"]] == ["GLM-5"]
    assert [r["model"] for r in results["reviewers"]] == ["gpt-5.2"]
