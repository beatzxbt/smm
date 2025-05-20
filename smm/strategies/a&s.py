import asyncio

from framework.tools.logger import Logger
from smm.strategies.base import BaseStrategy

class AAndSStrategy(BaseStrategy):
    def __init__(self, params: dict, logger: Logger, producer_queues: list[asyncio.Queue]):
        super().__init__(params, logger, producer_queues)
        