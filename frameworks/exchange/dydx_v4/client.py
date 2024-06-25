from frameworks.exchange.base.client import Client


class DydxClient(Client):
    recv_window = 1000

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret) # NOTE: Ignored, SDK in use
        
        # NOTE: All methods below initialized in exchange warm-up
        #
        # self.node = NodeClient()
        # self.indexer = IndexerClient()
        # self.market = Market()
        # self.wallet = Wallet()

    def sign_headers(self, method, headers):
        pass

    def error_handler(self, recv):
        pass
