from orchid_ng.services.config import ConfigService


def test_singleton():
    params_service = ConfigService()
    assert params_service.run_dir is not None
    assert id(params_service) == id(ConfigService())


def test_change_param():
    ConfigService().run_dir = "test"
    assert ConfigService().run_dir == "test"
