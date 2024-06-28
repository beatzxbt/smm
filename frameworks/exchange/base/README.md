# System Breakdown

#### Link to full Twitter thread here: []

Each exchange's structure involves two main parts, the market/private websocket data ingestion and the exchange's REST facing API (ordering, requesting data snapshots, etc). Each built independent of the sharedstate, which acts as the central hub for connecting the websocket/exchange interface to the rest of the system.

The goal of these parts are to provide a consistant, universal API which one can write strategies with, whilst the translation required between this internal API to a form that the exchange's API understand, is taken care of behind the curtains. This allows one's code to focus solely on the money making, boosting productivity. 

Now, you may be familiar with [CCXT](https://github.com/ccxt/ccxt), a very well built and maintained library which aims to fulfil the same goals! The difference between the structures provided here and the ones provided by CCXT are, that, here a large layer of safety has been removed in favor of speed. Functionality related to moving funds, flexibility with input types, etc, is not required here. The level of strictness is expected to be higher, and errors are intended to show up quickly if functions are used incorrectly. However, when used correctly, it is more efficient and faster.

Though, to reduce maintainance on the repository, some integrations involve using the official Python clients/wrappers of their respective APIs. These fall smoothly into the base classes provided, keeping it *somewhat* unnoticeable in the strategy side. Normally for CEX's, these wrappers will tend to be slower as they are more flexible for the average user to interact with, meanwhile, as common for official DEX wrappers like the [Dydx V4 API](https://github.com/dydxprotocol/v4-clients/tree/main/v4-client-py), have faster signing implementations in non-python wrappers and use FFI (call another language's code) to provide this speed boost. 

I will personally be maintaining some exchanges anyways (eg Binance, Bybit, Okx) as it falls inline with my private system's maintainance, however am still happy to patch fixes on other APIs if reported. My contact info can be found at the bottom [here](/README.md).


Exchange
--------
This class aims to be the central point for all REST-related API communication. It houses the API key/secret, client, message formatting and order id generator classes. Its functions provide clear access to essential endpoints, such as polling market/private data and creating/amending/cancelling orders. Additional functions can easily be added if required in the specific strategy, accessed in the same way as the essential functions. 

Each function follows a simple routine:
* Index the relevant endpoint & HTTP method.
* Generate a filled header/parameter.
* Send a request to the API.

There are also utility functions required as part of the exchange class, such as `shutdown()`. These are safeties that one *is highly recommended* to add to their main.py or the central trading loop. In the event of a failure in the system that propagates to the highest level, the `shutdown()` function will actively try cancel all outstanding orders on the selected symbol, as well as attempt to neutralize the open position (if existing). 

This class is accessible from the sharedstate by doing "sharedstate.exchange".

My implementation for the Binance API can be found [here](/frameworks/exchange/binance/exchange.py) 


Websocket
---------
This class is the central point for all data ingess API communication. Its simple job is to:
* Open a websocket feed for the following market data:
    * Orderbook
    * Trades
    * Ticker
    * Candlesticks

* Open a websocket feed for the following private data:
    * Open orders 
    * Open position
    * Executions (Fills of your own orders)
    * Wallet/Account 

It works by performing the following steps for each websocket message recieved:
* Match the message's topic to its respective handler/processor
* Filter relevant message data and convert types if neccessary
* Map to internal data structure (well documented [here](/frameworks/exchange/base/ws_handlers))
* Copy the internal data structure and modify the data in the sharedstate's data dictionary. 

The class also handles all communication to the exchange's websocket API, with a `send()` function for subscriptions. There is integrated reconnection logic, for unintentional disconnections or errors.

``start()`` and ``stop()`` functions are provided to cleanly create/close async sessions when needed.

The core websocket logic is found [here](/frameworks/exchange/base/websocket.py), whilst the Bybit implementation can be found [here](/frameworks/exchange/bybit/websocket.py). Both are extensively documented and it is recommended to go through them to get a better grasp of its functions. 

*NOTE: The websocket connection framework can seamlessly support multiple streams concurrently, however the sharedstate and the websocket handlers are only designed for single symbol use at the moment.*


Client
------
This class aims to handle all low level connectivity to the exchange API. It recieves references of the API key/secret, and requires implementations of error handling & signing functions for endpoints which require authentication. 

The error handling function aims to provide a simple aim of determining whether an error is known or unknown, and whether the client should keep trying to send the request if it has failed previously. This also provides an opportunity to rewrite long errors messages from the API in a more readable form. 

The signing function varies from exchange to exchange, but moreso for DEXs where different chains have vastly different signing methods. Sometimes, signing for different HTTP methods can vary and hence its a required field. Here, the flow is; an unsigned header goes in, and out comes a formatted, signed header following the exchange's defined spec.

A request from the client follows the steps: 
* Sign the header if required.
* Submit a request to the exchange API with the provided information.
* Once recieved, ensure the HTTP response code is successful.
    * If unsuccessful, retry.
* Pass the response's contents to the error handler, doing another pass to check the exchange's error code. 
    * If unsuccessful, retry if required otherwise return an empty response.
* Return the successful response.

My implementation for the Bybit API can be found [here](/frameworks/exchange/bybit/client.py) 


Endpoints
---------
This class aims to provide a normalized interface to access all required & optional endpoints from the exchange & websocket manager classes. It wraps each endpoint in an Endpoint class, making the url and method fast but clean to access. As it as no moving parts, it is initialized at the start of the classes using it and therefore has less care for startup speed, but more for access speed & safety.

Adding an endpoint & accessing it is fairly straightforward, and is well documented [here](/frameworks/exchange/base/endpoints.py). The [Binance implementation](/frameworks/exchange/binance/endpoints.py) can also provide some useful context in understanding how this structure works.


Formats & Types
--------------- 
These class manages most of the translation between the normalized API and exchange-spec API. Used together, they take in some form of normalized information, map it to a format that the exchange requires (including converting things like order type & order side) and return a format ready to send to the client.

Once again, it has a set of required functions (indentical to the exchange class), with an easy way to add supporting format functions to the additional functions in the exchange class.

Making these translation functions is very straight forward, and [this Bybit implementation](/frameworks/exchange/bybit/formats.py) should be enough to understand how it all works. The supporting order side/type converters can be found [here](/frameworks/exchange/binance/types.py), with the full implementation found [here](/frameworks/exchange/base/types.py).

Order IDs
--------
A class that's need arose with my struggles of dealing with rate limits & modifying large sets of orders. This aims to provide a normalized interface which generates exchange-spec order IDs, which can are assosiated with orders when sent (and recieved from the exchange). 

This class is initialized within the exchange class and is accessed by doing "sharedstate.exchange.orderid". [This Bybit implementation](/frameworks/exchange/bybit/orderid.py) and its [base class](/frameworks/exchange/base/orderid.py) has helpful docstrings to better understand it.


# Integration Guide
abc
