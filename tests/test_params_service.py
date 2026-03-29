from orchid_ng.services.params import ParamsService


def test_basic():
    params_service = ParamsService()
    assert params_service.run_dir is not None
    assert id(params_service) == id(ParamsService())
