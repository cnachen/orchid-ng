import pytest

from orchid_ng.prompts.load import PromptLoader

prompt_loader = PromptLoader()

def test_load_normal():
    prompt = prompt_loader.load("review-idea.txt")
    assert prompt is not None

def test_load_normal_suffix():
    prompt = prompt_loader.load("review-idea")
    assert prompt is not None
    prompt = prompt_loader.load("review-idea.txt")
    assert prompt is not None

def test_load_non_exists():
    with pytest.raises(FileNotFoundError):
        prompt_loader.load("non-exists.txt")
