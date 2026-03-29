from orchid_ng.utils.singleton import SingletonMeta


class ConfigService(metaclass=SingletonMeta):
    def __init__(self) -> None:
        self.run_dir = ".runs"
        self.iterations = 100
        self.action_limits = 4
