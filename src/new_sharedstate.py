import tomli

class NewSharedState:

    def __init__(
        self,
        #All the default argumentes are defined in the parser arguments (main.py)
        key_arg,
        ticker_arg
    ) -> None:
        self.load_config(
            #This it the optional key argument for the load config 
            key_arg
        )
        self.load_settings(
            #This is the optional ticker argument
            ticker_arg
        )

        None


    def load_config(self, key_arg):
        with open("config/bybit.toml", "rb") as f:
            config = tomli.load(f)
            matching_keys = [key for key in config.keys() if key.endswith(key_arg) or (key_arg == "1" and key == "api_key")]

            #If the user has some type of plugin for toml, the file will already give a trigger about this
            if len(matching_keys) != 1:
                raise ValueError("There are more or less than one API key/secret of number: ", key_arg)
            match_key = str(matching_keys[0])
            if len(config[match_key]["api_key"]) > 0 and len(config[match_key]["api_secret"]) > 0:
                self.api_key = config[match_key]["api_key"]
                self.api_secret = config[match_key]["api_secret"]
            else:
                raise ValueError("Missing API key/secret of number: ", key_arg)

    def load_settings(self, ticker_arg):
        with open("config/config.toml", "rb") as f:
            settings = tomli.load(f)
            #Binance symbol
            binance_symbol_key = self.find_matching_keys(settings, "binance_symbol", ticker_arg)
            self.binance_symbol = settings[binance_symbol_key]["symbol"]
            self.binance_tick_size = settings[binance_symbol_key]["tick_size"]
            self.binance_lot_size = settings[binance_symbol_key]["lot_size"]
            #Bybit symbol
            bybit_symbol_key = self.find_matching_keys(settings, "bybit_symbol", ticker_arg)
            self.bybit_symbol = settings[bybit_symbol_key]["symbol"]
            self.bybit_tick_size = settings[bybit_symbol_key]["tick_size"]
            self.bybit_lot_size = settings[bybit_symbol_key]["lot_size"]    
            #Primary date feed
            self.primary_date_feed = settings["data_feed"]["primary"]        

            print(self.binance_symbol)

    # This will find the matching key, or the default value
    # Settings -> is always the settigns loaded by tomli
    # base_section -> is the base name of the section/config ex: binance_symbol
    # arg -> is the argument given by the user of the defualt value
    def find_matching_keys(self, settings, base_section, arg):
        if arg == str(''):
            match_key = base_section
        else: 
            matching_keys = [
                key for key in settings.keys() 
                if key.startswith(str(base_section)) and
                key.endswith(str(arg))
            ]
            print(matching_keys)
            if len(matching_keys) != 1:
                raise ValueError("There are more or less sections with the same name of: ", arg)
            match_key = matching_keys[0]

        return match_key
