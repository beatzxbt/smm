import sys
import os

# Get the absolute path to the project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the project root directory to sys.path
sys.path.insert(0, project_root)


import asyncio

from strategy.core import Strategy
from settings import StrategyParameters
from frameworks.sharedstate.market import MarketDataSharedState
from frameworks.sharedstate.private import PrivateDataSharedState



async def main(configuration_directory: str, parameter_directory: str):
    mdss = MarketDataSharedState(configuration_directory, parameter_directory)
    pdss = PrivateDataSharedState(configuration_directory, parameter_directory)
    params = StrategyParameters(parameter_directory)

    # rememeber the data feeds being ran from sharedstate still needs to be
    # implemented. Modify any behaviour if it turns the mdss class a bit funny 
    # this also means that refreshing parameters will be managed within the class
    # and not outsourced into the strategy/main file, cluttering it 
    await Strategy(mdss, pdss, params).run()


if __name__ == "__main__":
    CONFIGURATION_DIR = ""
    PARAMETERS_DIR = ""

    asyncio.run(main(CONFIGURATION_DIR, PARAMETERS_DIR))
