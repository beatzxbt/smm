# System Breakdown

#### Link to full Twitter thread here: []

Each exchange's structure involves two main parts, the market/private websocket data ingestion and the exchange's REST facing API (ordering, requesting data snapshots, etc). Each built independent of the sharedstate, which acts as the central hub for connecting the websocket/exchange interface to the rest of the system.

The goal of these parts are to provide a consistant, universal API which one can write strategies with, whilst the translation required between this internal API to a form that the exchange's API understand, is taken care of behind the curtains. This allows one's code to focus solely on the money making, boosting productivity. 

Now, you may be familiar with [CCXT](https://github.com/ccxt/ccxt), a very well built and maintained library which aims to fulfil the same goals! The difference between the structures provided here and the ones provided by CCXT are, that, here a large layer of safety has been removed in favor of speed. Functionality related to moving funds, flexibility with input types, etc, is not required here. The level of strictness is expected to be higher, and errors are intended to show up quickly if functions are used incorrectly. However, when used correctly, it is more efficient and faster.

### Exchange
This class aims to be the central point for all REST-related API communication. It houses the API key/secret, client, message formatting and order id generator classes. Its functions provide clear access to essential endpoints, such as polling market/private data and creating/amending/cancelling orders. Additional functions can easily be added if required in the specific strategy, accessed in the same way as the essential functions. 

Each function follows a simple routine:
* Index the relevant endpoint & HTTP method.
* Generate a filled header/parameter.
* Send a request to the API.

There are also utility functions required as part of the exchange class, such as shutdown(). These are safeties one *is highly recommended* to add to their main.py or whatever central trading script. In the event of a failure in the system that propagates to the highest level, the shutdown() function will actively try cancel all outstanding orders on the selected symbol, as well as attempt to neutralize the open position( if existing). 

This class is accessible from the sharedstate by doing "sharedstate.exchange".

My implementation for the Binance API can be found [here](/frameworks/exchange/binance/exchange.py) 

### Client
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

### Endpoints
This class aims to provide a normalized interface to access all required & optional endpoints from the exchange & websocket manager classes. It wraps each endpoint in an Endpoint class, making the url and method fast but clean to access. As it as no moving parts, it is initialized at the start of the classes using it and therefore has less care for startup speed, but more for access speed & safety.

Adding an endpoint & accessing it is fairly straightforward, and is well documented [here](/frameworks/exchange/base/endpoints.py). The [Binance implementation](/frameworks/exchange/binance/endpoints.py) can also provide some useful context in understanding how this structure works.

### Formats & Types 
These class manages most of the translation between the normalized API and exchange-spec API. Used together, they take in some form of normalized information, map it to a format that the exchange requires (including converting things like order type & order side) and return a format ready to send to the client.

Once again, it has a set of required functions (indentical to the exchange class), with an easy way to add supporting format functions to the additional functions in the exchange class.

Making these translation functions is very straight forward, and [this Bybit implemenation](/frameworks/exchange/bybit/formats.py) should be enough to understand how it all works. The supporting order side/type converters can be found [here](/frameworks/exchange/binance/types.py), with the full implementation found [here](/frameworks/exchange/base/types.py).


# Integration Guide
abc
