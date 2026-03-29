from orchid_ng.services.config import ConfigService
from datetime import datetime


def test_singleton():
    params_service = ConfigService()
    assert params_service.runs_dir is not None
    assert id(params_service) == id(ConfigService())


def test_change_param():
    ConfigService().runs_dir = "test"
    assert ConfigService().runs_dir == "test"
