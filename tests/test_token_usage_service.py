import json

import pytest

from orchid_ng.services.config import ConfigService
from orchid_ng.services.token_usage import TokenUsageService
from orchid_ng.utils.singleton import SingletonMeta


def _reset_singletons() -> None:
    SingletonMeta._instances.clear()


def test_append_writes_jsonl(tmp_path):
    _reset_singletons()

    config = ConfigService()
    config.current_run_dir = tmp_path

    service = TokenUsageService()
    service.append(
        tag="stage1", prompt_tokens=1, completion_tokens=2, total_tokens=3, model="m1"
    )

    content = (
        (tmp_path / "token_usage.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    )
    assert len(content) == 1

    obj = json.loads(content[0])
    assert obj["tag"] == "stage1"
    assert obj["model"] == "m1"
    assert obj["prompt_tokens"] == 1
    assert obj["completion_tokens"] == 2
    assert obj["total_tokens"] == 3


def test_append_from_litellm_extracts_usage(tmp_path):
    _reset_singletons()

    config = ConfigService()
    config.current_run_dir = tmp_path

    service = TokenUsageService()
    service.append_from_litellm(
        tag="stage2",
        group="reviewers",
        response={
            "model": "gpt-5.2",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        },
        meta={"x": 1},
    )

    line = (tmp_path / "token_usage.jsonl").read_text(encoding="utf-8").strip()
    obj = json.loads(line)
    assert obj["tag"] == "stage2"
    assert obj["group"] == "reviewers"
    assert obj["model"] == "gpt-5.2"
    assert obj["prompt_tokens"] == 10
    assert obj["completion_tokens"] == 20
    assert obj["total_tokens"] == 30
    assert obj["meta"] == {"x": 1}


def test_append_rejects_empty_tag(tmp_path):
    _reset_singletons()

    config = ConfigService()
    config.current_run_dir = tmp_path

    service = TokenUsageService()
    with pytest.raises(ValueError):
        service.append(tag="   ")
