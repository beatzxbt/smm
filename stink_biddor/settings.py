from frameworks.config.custom_parameters import CustomParameters

class StrategyParameters(CustomParameters):
    def load_settings(self, settings):
        self.symbol = str(settings["symbol"])
        self.stink_levels = list(settings["stink_levels"])
