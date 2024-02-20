import json
import hmac
import hashlib
from typing import List, Tuple
from src.utils.misc import time_ms

class BybitPrivateWs:
    """
    Manages the WebSocket connection for Bybit's private streams, including authentication and subscription requests.

    Attributes
    ----------
    key : str
        The API key for authentication.
    secret : str
        The API secret for authentication.
    expires : str
        The expiry time for the authentication message.

    Methods
    -------
    authentication() -> str:
        Generates an authentication payload for a private WebSocket connection.
    multi_stream_request(topics: List[str]) -> Tuple[str, List[str]]:
        Creates a WebSocket request for subscribing to multiple topics.
    """

    def __init__(self, key: str, secret: str) -> None:
        """
        Initializes the BybitPrivateWs with API credentials and an expiry time for the authentication.

        Parameters
        ----------
        key : str
            The API key for Bybit.
        secret : str
            The API secret for Bybit.
        """
        self.key = key
        self.secret = secret
        self.expires = str(time_ms() + 5000)

    def authentication(self) -> str:
        """
        Constructs the authentication payload for establishing a private WebSocket connection.

        Returns
        -------
        str
            The authentication payload as a JSON string.
        """
        signature = hmac.new(
            key=bytes(self.secret, "utf-8"),
            msg=bytes(f"GET/realtime{self.expires}", "utf-8"),
            digestmod=hashlib.sha256,
        ).hexdigest()

        return json.dumps({
            "op": "auth",
            "args": [self.key, self.expires, signature],
        })

    def multi_stream_request(self, topics: List[str]) -> Tuple[str, List[str]]:
        """
        Generates a request for subscribing to multiple private topics.

        Parameters
        ----------
        topics : List[str]
            A list of topics to subscribe to, such as "Position", "Execution", and "Order".

        Returns
        -------
        Tuple[str, List[str]]
            A tuple containing the subscription request as a JSON string and a list of topics.
        """
        list_of_topics = []
        for topic in topics:
            if topic == "Position":
                list_of_topics.append("position")
            elif topic == "Execution":
                list_of_topics.append("execution")
            elif topic == "Order":
                list_of_topics.append("order")

        req = json.dumps({"op": "subscribe", "args": list_of_topics})
        return req, list_of_topics