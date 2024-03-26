import asyncio
from frameworks.exchange.base.rest.exchange import Exchange
from frameworks.exchange.brrr.bybit.endpoints import BybitEndpoints
from frameworks.exchange.brrr.bybit.formats import BybitFormats
from frameworks.exchange.brrr.bybit.client import BybitClient
from frameworks.sharedstate import SharedState
from typing import Dict


class Bybit(Exchange):
    def __init__(self, ss: SharedState) -> None:
        self.ss = ss
        self.endpoints = BybitEndpoints
        self.formats = BybitFormats()
        self.client = BybitClient(self.__api__)
        super().__init__(self.client, self.endpoints, self.formats)

    @property
    def __api__(self) -> Dict:
        return self.ss.private["bybit"]["API"]