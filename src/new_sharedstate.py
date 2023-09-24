import tomli

class NewSharedState:

    def __init__(
        self,
        #All the default argumentes are defined in the parser arguments (main.py)
        key_arg,
        ticker_arg,
        feed_arg,
        sizef_arg,
        size_arg
    ) -> None:
        self.load_config(
            #This it the optional key argument for the load config 
            key_arg
        )
        self.load_settings(
            #This is the optional ticker argument
            ticker_arg,
            feed_arg,
            sizef_arg,
            size_arg,
        )
        print(self.api_key)
        None


    def load_config(self, key_arg):
        with open("config/bybit.toml", "rb") as f:
            config = tomli.load(f)
            self.api_key = self.get_config_value(config["api_key"], key_arg, "api_key")
            self.api_secret = self.get_config_value(config["api_key"], key_arg, "api_secret")

    def load_settings(
        self, 
        ticker_arg,
        feed_arg,
        sizef_arg,
        size_arg
    ):

        with open("config/config.toml", "rb") as f:
            settings = tomli.load(f)
            #Binance symbol
            self.binance_symbol = self.get_config_value(settings["binance_symbol"], ticker_arg, "symbol")
            self.binance_tick_size = self.get_config_value(settings["binance_symbol"], ticker_arg, "tick_size")
            self.binance_lot_size = self.get_config_value(settings["binance_symbol"], ticker_arg, "lot_size")
            #Bybit symbol
            self.bybit_symbol = self.get_config_value(settings["bybit_symbol"], ticker_arg, "symbol")
            self.bybit_tick_size = self.get_config_value(settings["bybit_symbol"], ticker_arg, "tick_size")
            self.bybit_lot_size = self.get_config_value(settings["bybit_symbol"], ticker_arg, "lot_size")
            #Primary date feed
            self.primary_data_feed = self.get_config_value(settings["data_feed"], feed_arg, "feed")  
            #Buffer
            self.buffer = int(self.get_config_value(settings["buffer"], None, "buffer"))
            #Account size
            if size_arg is not None:
                self.account_size = int(size_arg)
            else:
                self.account_size = int(self.get_config_value(settings["account"], sizef_arg, "size"))
            #Volatility indicator
            self.bb_length = int(self.get_config_value(settings["volatility"], None, "bollinger_band_length"))
            self.bb_std = int(self.get_config_value(settings["volatility"], None, "bollinger_band_std"))
            #Master offsets
            self.quote_offset = int(self.get_config_value(settings["offsets"], None, "quote_offset"))
            self.size_offset = int(self.get_config_value(settings["offsets"], None, "size_offset"))
            self.volatility_offset = int(self.get_config_value(settings["offsets"], None, "volatility_offset"))

            print(settings["strategies"])

    
    def get_config_value(self, arr, arg, key):
        """
        Retrieve a configuration value from a JSON array.

        This function retrieves a configuration value based on the specified arguments.
        
        Args:
            arr (dict): The JSON array containing configuration settings.
            arg (str): The specific category within the array. Use None for default settings.
            key (str): The key corresponding to the setting to retrieve.

        Returns:
            The value corresponding to the specified key in the configuration.

        Raises:
            ValueError: If the category or key does not exist in the configuration.
        """
        if arg is None:
            default_config = arr.get("default")
            if default_config and key in default_config:
                return default_config[key]
            else:
                raise ValueError("There is no default configuration or the key does not exist.")
        else:
            specific_config = arr.get(arg)
            if specific_config and key in specific_config:
                return specific_config[key]
            else:
                raise ValueError(f"There is no configuration for '{arg}' or the key does not exist.")
