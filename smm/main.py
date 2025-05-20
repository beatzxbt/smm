import os
import asyncio
import uvloop
import ruamel.yaml

from framework import load

from framework.tools.logger import Logger, LoggerConfig, FileLogHandler, DiscordLogHandler
from framework.base.exchange import BaseExchange
from framework.base.data import BaseMarketData, BasePrivateData


from smm.strategies import (
    BaseStrategy,
    PlainStrategy,
    AAndSStrategy,
    StinkyStrategy
)

PARAM_FILE = os.path.dirname(os.path.realpath(__file__)) + "/parameters.yaml"

class Smm:
    def __init__(self, api_key: str, api_secret: str, logger: Logger):
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger
        
        # No need for value checks after this point when referring to 
        # self.params as self.load_params() guarantees keys are present and 
        # values are within range. Otherwise an error will be thrown and the 
        # program halted.
        self.params = self.load_params(file_path=PARAM_FILE)

        # For now, there is only 1 data queue as their will 
        # only be one consumer (the strategy). In the future,
        # multiple queues may be added for different non-strategy 
        # consumers, such as a UI or a markout recorder.
        self.queues = [asyncio.Queue()]
        
        self.core_frameworks = load(self.params["exchange"])

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
        self.strategy: BaseStrategy = None

        match self.params["strategy"]:
            case 0:
                self.strategy = PlainStrategy(
                    exchange=self.exchange,
                    params=self.params,
                    logger=self.logger,
                    producer_queues=self.queues
                )
            case 1:
                self.strategy = AAndSStrategy(
                    exchange=self.exchange,
                    params=self.params,
                    logger=self.logger,
                    producer_queues=self.queues
                )
            case 2:
                self.strategy = StinkyStrategy(
                    exchange=self.exchange,
                    params=self.params,
                    logger=self.logger,
                    producer_queues=self.queues
                )
            
    def load_params(self, file_path: str) -> dict:
        with open(file_path, "r") as f:
            yaml_handler = ruamel.yaml.YAML()
            yaml_handler.indent(mapping=4, sequence=4, offset=2)
            yaml_handler.width = 4096
            yaml_handler.preserve_quotes = True
            params = yaml_handler.load(f)
            
            # Validate required keys are present
            required_keys = ["exchange", "symbol", "strategy", "parameters"]
            for key in required_keys:
                if key not in params:
                    raise ValueError(f"Missing required parameter: {key}")
            
            # Validate exchange value
            if not isinstance(params["exchange"], int) or params["exchange"] < 0 or params["exchange"] > 5:
                raise ValueError("Exchange must be an integer between 0 and 5")
            
            # Validate symbol value
            if not isinstance(params["symbol"], str) or not params["symbol"]:
                raise ValueError("Symbol must be a non-empty string")
            
            # Check if symbol ends with a valid quote currency
            valid_quote_currencies = ["USDT", "USD", "USDC"]
            symbol_valid = False
            for quote in valid_quote_currencies:
                if params["symbol"].upper().endswith(quote):
                    symbol_valid = True
                    break
            
            if not symbol_valid:
                raise ValueError(f"Symbol must end with one of: {', '.join(valid_quote_currencies)}")
            
            # Ensure symbol is properly formatted (uppercase)
            params["symbol"] = params["symbol"].upper()
            # Validate strategy value
            if not isinstance(params["strategy"], int) or params["strategy"] < 0 or params["strategy"] > 2:
                raise ValueError("Strategy must be an integer between 0 and 2")
            
            # Validate parameters based on strategy
            if "common" not in params["parameters"]:
                raise ValueError("Missing common parameters")
            
            # Validate common parameters
            common = params["parameters"]["common"]
            if "total_orders" not in common or "max_usd_position" not in common:
                raise ValueError("Missing required common parameters")
            
            # Validate strategy-specific parameters
            strategy_type = params["strategy"]
            if strategy_type == 0 and "plain" not in params["parameters"]:
                raise ValueError("Missing plain strategy parameters")
            elif strategy_type == 0:
                plain = params["parameters"]["plain"]
                if "minimum_spread" not in plain or "aggressiveness" not in plain:
                    raise ValueError("Missing required plain strategy parameters")
                if not 0.0 <= plain["aggressiveness"] <= 1.0:
                    raise ValueError("Aggressiveness must be between 0.0 and 1.0")
            
            elif strategy_type == 1 and "a&s" not in params["parameters"]:
                raise ValueError("Missing a&s strategy parameters")
            elif strategy_type == 1:
                if "vol" not in params["parameters"]["a&s"]:
                    raise ValueError("Missing required a&s strategy parameters")
            
            elif strategy_type == 2 and "stinky" not in params["parameters"]:
                raise ValueError("Missing stinky strategy parameters")
            elif strategy_type == 2:
                stinky = params["parameters"]["stinky"]
                if "minimum_spread" not in stinky or "maximum_spread" not in stinky:
                    raise ValueError("Missing required stinky strategy parameters")
            
            return params
        
    async def run(self):
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
    async def main():
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
    
        # Load config and parameters
        try:
            yaml_handler = ruamel.yaml.YAML()
            yaml_handler.indent(mapping=4, sequence=4, offset=2)
            yaml_handler.width = 4096
            yaml_handler.preserve_quotes = True

            # Load environment variables
            load_dotenv()
            API_KEY = os.getenv(f"{EXCHANGE.upper()}_KEY")
            API_SECRET = os.getenv(f"{EXCHANGE.upper()}_SECRET")
            if not API_KEY or not API_SECRET:
                logger.error(f"Missing {EXCHANGE} API credentials in environment variables")
                raise ValueError(f"Missing {EXCHANGE} API credentials")
            
            # Load parameters
            with open(PARAM_FILE, "r") as f:
                params = yaml_handler.load(f)
                spec_params = params[f"stink{STINK_ID}"]
            if not spec_params or not params:
                logger.error(f"Missing spec_params or params for 'stink{STINK_ID}'")
                raise ValueError(f"Missing spec_params or params for 'stink{STINK_ID}'")

            logger.info(f"Loaded config and parameters for 'stink{STINK_ID}'; symbol: {spec_params[0]}")

        except Exception as e:
            logger.error(f"Error loading config or parameters; {e}")
            await logger.shutdown()
            await asyncio.sleep(1.0)
            raise e

        # Create strategy inside an async function
        strategy = BybitStrategy(
            logger=logger, 
            api_key=API_KEY, 
            api_secret=API_SECRET, 
            params=params,
            spec_params=spec_params
        )
        
        # Run the strategy
        await strategy.run()

    uvloop.run(main())