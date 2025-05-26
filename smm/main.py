import os
import asyncio
import uvloop
import ruamel.yaml

from framework import load_exchange

from framework.tools.logger import Logger, LoggerConfig, FileLogHandler
from framework.base.exchange import BaseExchange
from framework.base.data import BaseMarketData, BasePrivateData

from smm.strategies import load_strategy
from smm.strategies.base.strategy import BaseStrategy

PARAM_FILE = os.path.dirname(os.path.realpath(__file__)) + "/parameters.yaml"

class Smm:
    """Simple Market Maker (SMM) main class.
    
    This class orchestrates the market making strategy by loading parameters,
    initializing exchange connections, market data feeds, and the trading strategy.
    """
    
    def __init__(self, logger: Logger):
        """Initialize the SMM instance.
        
        Args:
            logger: Logger instance for logging messages.
        """
        self.logger = logger
        
        # No need for value checks after this point when referring to 
        # self.params as self.load_params() guarantees keys are present and 
        # values are within range. Otherwise an error will be thrown and the 
        # program halted.
        self.api_key = None
        self.api_secret = None
        self.params = self.load_params(file_path=PARAM_FILE)

        # For now, there is only 1 data queue as their will 
        # only be one consumer (the strategy). In the future,
        # multiple queues may be added for different non-strategy 
        # consumers, such as a UI or a markout recorder.
        self.queues = [asyncio.Queue()]
        
        self.core_frameworks = load_exchange(self.params["exchange"])

        # Split up the core frameworks into their own variables 
        # for cleaner access.
        self.exchange: BaseExchange = self.core_frameworks[0](
            api_key=self.api_key, 
            api_secret=self.api_secret, 
            logger=self.logger
        )
        self.market_data: BaseMarketData = self.core_frameworks[1](
            symbols=[self.params["symbol"]], 
            logger=self.logger, 
            consumer_queues=self.queues
        )
        self.private_data: BasePrivateData = self.core_frameworks[2](
            api_key=self.api_key,
            api_secret=self.api_secret,
            symbols=[self.params["symbol"]], 
            logger=self.logger, 
            consumer_queues=self.queues
        )
        self.strategy: BaseStrategy = load_strategy(self.params["strategy"])(
            exchange=self.exchange,
            params=self.params,
            logger=self.logger,
            producer_queues=self.queues
        )
            
    def load_params(self, file_path: str) -> dict:
        """Loads the parameters from the file and validates them.

        Args:
            file_path: The path to the parameters file.

        Returns:
            The validated parameters dictionary.
            
        Raises:
            ValueError: If any required parameters are missing or invalid.
        """
        with open(file_path, "r") as f:
            yaml_handler = ruamel.yaml.YAML()
            yaml_handler.indent(mapping=4, sequence=4, offset=2)
            yaml_handler.width = 4096
            yaml_handler.preserve_quotes = True
            params = yaml_handler.load(f)
            
            self._validate_required_keys(params)
            self._validate_exchange(params)
            self._validate_symbol(params)
            self._validate_strategy(params)
            self._validate_parameters(params)
            
            return params
    
    def _validate_required_keys(self, params: dict) -> None:
        """Validate that all required top-level keys are present.
        
        Args:
            params: The parameters dictionary to validate.
            
        Raises:
            ValueError: If any required keys are missing.
        """
        required_keys = ["exchange", "symbol", "strategy", "parameters"]
        for key in required_keys:
            if key not in params:
                raise ValueError(f"Missing required parameter: {key}")
    
    def _validate_exchange(self, params: dict) -> None:
        """Validate exchange parameter.
        
        Args:
            params: The parameters dictionary containing the exchange value.
            
        Raises:
            ValueError: If exchange value is not an integer between 0-6.
        """
        exchange = params["exchange"]
        if not isinstance(exchange, int) or exchange < 0 or exchange > 6:
            raise ValueError(f"Invalid exchange value; expected 0-6 but got {exchange}")
    
    def _validate_symbol(self, params: dict) -> None:
        """Validate and format symbol parameter.
        
        Args:
            params: The parameters dictionary containing the symbol value.
            
        Raises:
            ValueError: If symbol is invalid or has unsupported quote currency.
        """
        symbol = params["symbol"]
        if not isinstance(symbol, str) or not symbol:
            raise ValueError(f"Invalid symbol; expected a non-empty string but got {symbol}")
        
        # Check if symbol ends with a valid quote currency
        valid_quote_currencies = ["USDT", "USD", "USDC"]
        symbol_valid = any(symbol.upper().endswith(quote) for quote in valid_quote_currencies)
        
        if not symbol_valid:
            raise ValueError(f"Invalid quote currency; expected one of: {', '.join(valid_quote_currencies)} but got {symbol}")
        
        # Ensure symbol is properly formatted for each exchange
        match params["exchange"]:
            case 0: # Binance
                params["symbol"] = symbol.lower()
            case 1: # Bybit
                params["symbol"] = symbol.upper()
            case 2: # OKX
                params["symbol"] = symbol.upper()
            case _:
                pass
    
    def _validate_strategy(self, params: dict) -> None:
        """Validate strategy parameter.
        
        Args:
            params: The parameters dictionary containing the strategy value.
            
        Raises:
            ValueError: If strategy value is not an integer between 0-2.
        """
        strategy = params["strategy"]
        if not isinstance(strategy, int) or strategy < 0 or strategy > 2:
            raise ValueError(f"Invalid strategy; expected 0-2 but got {strategy}")
    
    def _validate_parameters(self, params: dict) -> None:
        """Validate strategy parameters section.
        
        Args:
            params: The parameters dictionary containing the parameters section.
            
        Raises:
            ValueError: If common parameters section is missing.
        """
        if "common" not in params["parameters"]:
            raise ValueError("Missing common parameters; expected a dictionary with keys: total_orders, max_usd_position")
        
        self._validate_common_parameters(params["parameters"]["common"])
    
    def _validate_common_parameters(self, common: dict) -> None:
        """Validate common parameters.
        
        Args:
            common: The common parameters dictionary to validate.
            
        Raises:
            ValueError: If any required common parameters are missing.
        """
        required_common = ["total_orders", "max_usd_position"]
        for param in required_common:
            if param not in common:
                raise ValueError(f"Missing required common parameter: {param}")
    
    async def run(self) -> None:
        """Runs the strategy.
        
        This method starts all necessary components (exchange connection, market data,
        private data, and strategy) and handles graceful shutdown on cancellation or errors.
        """
        tasks: list[asyncio.Task] = []
        try:
            await self.exchange.connect_ws_client()
            tasks = [
                asyncio.create_task(self.market_data.start()),
                asyncio.create_task(self.private_data.start()),
                asyncio.create_task(self.strategy.start())
            ]
            await asyncio.gather(*tasks)
        except asyncio.CancelledError or KeyboardInterrupt:
            self.logger.info("Strategy cancelled; shutting down...")
        except Exception as e:
            self.logger.error(f"Error running strategy; {e}")
        finally:
            # Cancel all tasks. This will automatically start 
            # internal shutdown sequences within each task handling
            # things like order cancellation, etc.
            for task in tasks:
                task.cancel()
            
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass
            
            await asyncio.sleep(1.0)
            
            await self.exchange.close_all_clients()
            await self.logger.shutdown()

            return
    
if __name__ == "__main__":
    async def main() -> None:
        """Main entry point for the SMM application.
        
        Sets up logging configuration and runs the SMM strategy.
        """
        logger = Logger(
            config=LoggerConfig(
                base_level="INFO", 
                stout=True, 
                max_buffer_size=100, 
                max_buffer_age=5
            ),
            name="SMM",
            handlers=[
                FileLogHandler(
                    filename=os.path.dirname(os.path.realpath(__file__)) + "/logs.txt",
                    buffer_size=100,
                    flush_interval=5,
                ),
            ]
        )
    
        # Run the strategy
        await Smm(logger=logger).run()

    uvloop.run(main())