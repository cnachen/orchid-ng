import os

from orchid_ng.config.settings import Settings


def test_settings_auto_loads_dotenv(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=test-from-dotenv\n", encoding="utf-8"
    )

    Settings(project_root=tmp_path)

    assert os.environ["OPENAI_API_KEY"] == "test-from-dotenv"


def test_settings_does_not_override_existing_env(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "already-set")
    (tmp_path / ".env").write_text(
        "OPENAI_API_KEY=test-from-dotenv\n", encoding="utf-8"
    )

    Settings(project_root=tmp_path)

    assert os.environ["OPENAI_API_KEY"] == "already-set"
