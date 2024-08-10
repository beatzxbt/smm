import orjson
import hashlib
import hmac

from frameworks.exchange.base.structures.table import Table as ErrorTable
from frameworks.exchange.base.client import Client


class BinanceClient(Client):
    recv_window = 1000

    def __init__(self, api_key: str, api_secret: str) -> None:
        super().__init__(api_key, api_secret)

        self.base_headers = {
            "X-MBX-APIKEY": self.api_key,
        }

        self._error_table_ = ErrorTable(missing_key_error="Unknown code...")
        self._error_table_.add(0, (False, ""))
        self._error_table_.add(200, (False, ""))
        self._error_table_.add(1003, (False, "Rate limits exceeded!"))
        self._error_table_.add(1015, (False, "Rate limits exceeded!"))
        self._error_table_.add(1008, (True, "Server overloaded..."))
        self._error_table_.add(1021, (True, "Out of recvWindow..."))
        self._error_table_.add(1111, (False, "Incorrect tick/lot size..."))
        self._error_table_.add(4029, (False, "Incorrect tick/lot size..."))
        self._error_table_.add(4030, (False, "Incorrect tick/lot size..."))
        self._error_table_.add(1125, (False, "Invalid listen key..."))
        self._error_table_.add(2010, (False, "Order create rejected..."))
        self._error_table_.add(2011, (False, "Order cancel rejected..."))
        self._error_table_.add(2012, (False, "Order cancel all rejected..."))
        self._error_table_.add(2013, (False, "Order does not exist..."))
        self._error_table_.add(2014, (False, "Invalid API key format"))
        self._error_table_.add(2018, (False, "Insufficient balance..."))
        self._error_table_.add(3000, (True, "System busy. Please try again later."))
        self._error_table_.add(3001, (False, "Trading is suspended for this symbol."))
        self._error_table_.add(3002, (False, "Order has been filled or canceled."))
        self._error_table_.add(3003, (False, "Order was not found."))
        self._error_table_.add(3004, (False, "Insufficient funds in your account."))
        self._error_table_.add(3005, (False, "Margin call failed. Please add more funds."))
        self._error_table_.add(3006, (False, "Position size exceeds the maximum limit."))
        self._error_table_.add(3007, (False, "Position already exists. Cannot open a new position."))
        self._error_table_.add(3008, (False, "Duplicate order detected."))
        self._error_table_.add(3009, (False, "Invalid leverage setting."))
        self._error_table_.add(3010, (False, "Position liquidation in progress."))
        self._error_table_.add(3011, (False, "API key permissions are insufficient for this action."))
        self._error_table_.add(3012, (False, "Order amount is too small."))
        self._error_table_.add(3013, (False, "Order amount exceeds the maximum limit."))
        self._error_table_.add(3014, (False, "The trading pair is not available."))
        self._error_table_.add(3015, (False, "The order price is out of the allowed range."))

    def sign_headers(self, method, headers):
        hash_signature = hmac.new(
            key=self.api_secret.encode(),
            msg=orjson.dumps(headers),
            digestmod=hashlib.sha256,
        )
        headers["signature"] = hash_signature.hexdigest()
        return headers

    def error_handler(self, recv):
        return self._error_table_.get(int(recv.get("code", 0)))
        