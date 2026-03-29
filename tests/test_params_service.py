from orchid_ng.services.params import ParamsService


def test_singleton():
    params_service = ParamsService()
    assert params_service.run_dir is not None
    assert id(params_service) == id(ParamsService())


def test_change_param():
    ParamsService().run_dir = "test"
    assert ParamsService().run_dir == "test"
