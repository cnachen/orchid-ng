from orchid_ng.services.config import ConfigService
from pathlib import Path


def test_singleton():
    params_service = ConfigService()
    assert params_service.runs_dir is not None
    assert id(params_service) == id(ConfigService())


def test_change_param():
    ConfigService().runs_dir = Path("test")
    assert ConfigService().runs_dir == Path("test")
