<pre>
    ____        __    _ __     _____ __  _____  ___
   / __ )__  __/ /_  (_) /_   / ___//  |/  /  |/  /
  / __  / / / / __ \/ / __/   \__ \/ /|_/ / /|_/ / 
 / /_/ / /_/ / /_/ / / /_    ___/ / /  / / /  / /  
/_____/\__, /_.___/_/\__/   /____/_/  /_/_/  /_/   
      /____/                                       
A simple market making bot for Bybit
</pre>

***DISCLAIMER: This is a sample market making bot for [Bybit](https://www.bybit.com/en-US/). The bot can run 24/7 without being attended, however, please use at your own risk. If you are not ready to risk your own capital, but want to trade, you can sign up for Bybit's [testnet.bybit.com](https://testnet.bybit.com/en/). BeatzXBT will not accept liability for any loss or damage including, without limitation to, any loss of profit which may arise directly or indirectly from use of or reliance on this software.***

# Getting Started


### Clone the repository

In the terminal run the following commands:
```console
# Change directories to your workspace
$ cd /path/to/your/workspace

# Clone the repository
$ git clone git@github.com:beatzxbt/bybit-smm.git

# Change directories into the project
$ cd bybit-smm
```

__Note: Each terminal command going forward will be run within the main project directory.__

### Set Up the environment

Copy `.env.exmaple` to `.env`. This is where we are going to store our API keys:
```console 
$ cp .env.example .env
```

Next, you will need to create a Bybit account. __If you are not ready to trade real money, you can create a testnet account with no KYC required by signing up at [testnet.bybit.com](https://testnet.bybit.com/en/).__


Once you have created your Bybit account, generate API key and secret following [this guide](https://learn.bybit.com/bybit-guide/how-to-create-a-bybit-api-key/). Once you have your API keys, edit the `.env` file that you generated earlier, filling in your credentials:
```
API_KEY=YOUR_API_KEY_HERE
API_SECRET=YOUR_API_SECRET_HERE
```

_Optional: If you are using the testnet to trade, set the `TESTNET` flag to True within the `.env` file:_
```
TESTNET=True
```

### Install the requirements
_Optional: If you are familiar with viritual enironments, create one now and activate it. If not, this step is not necessary:_

```console
$ virtualenv venv
$ source venv/bin/activate
```

Install the package requirements:
```console
$ pip install -r requirements.txt
```

### Configure the trading parameters

Next, we are going to configure the parameters that actually determine which market we are making, and how the trader should behave. 

Sensible defaults are set in `parameters.yaml.example`. Copy it over to your `parameter.yaml` file to get started:
```console
$ cp parameters.yaml.example parameters.yaml
```

The `parameters.yaml` file is gitignored, and can be configured for each environment that you are trading in separately.

Each of the configurable parameters are explained below in more detail

- `account_size` ...
- `primary_data_feed` ...

- `binance_symbol`: ...
- `bybit_symbol`: ...

#### Master offsets 
subtitle...
- `quote_offset` ...
- `size_offset` ...
- `volatility_offset` ...


#### Market Maker Settings
subtitle...
- `base_spread` ...
- `min_order_size` ...
- `max_order_size` ...
-  `inventory_extreme` ...

#### Volatility settings
subtitle...
- `bollinger_band_length` ...
- `bollinger_band_std` ...


#### Running the bot

To run the the bot, once your `.env` and `parameters.yaml` file are configured, simply run:
```console
(venv) $ python3 -m main
```

__NOTE: If you are using MacOS, you may run into the following error__:
```
ssl.SSLCertVerificationError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1006)
```

The fix is [simple](https://stackoverflow.com/questions/52805115/certificate-verify-failed-unable-to-get-local-issuer-certificate).


# Strategy Design/Overview

1. Prices from Bybit (and optionally Binance) are streamed into a common shared class
2. A market maker function generates quotes, with bias based on price based features
  * Multiple features work on comparing orderbook, trades & price behaviours to calculate skew
  * Prices and quantities are generated, with prices within a volatility range, and min/max quantity defined manually
  * The above leads to behaviour shown in examples below:
    * (Ex) If binance mid price is lower than then bybit mid price -> skew is negative -> asks are more concentrated near mid price than bids
    * (Ex) If binance price is higher than then bybit price -> skew is positive -> bids have more qty than asks
    * (Ex) If inventory is extremely long, quotes are killed on the long side to try neutralize the position
3. Orders are sent to the exchange via diff function, which minimizes rate limit usage to shift between order states
  


# Contributions

The following improvements are WIP:

- Optional TWAP to reduce inventory (alongside purging quotes)
- Avellaneda and Stoikov's basic market making model
- More advanced orderbook & trades features
- __High Priority__ 
  - Setting up logger
  - Testing for order generation, get/post clients and websocket feeds 
- __Medium Priority__ 
  - Simpler execution and order feed handlers (reworked for time-based and orderId based indexing)
- __Low Priority__ 
  - Customized rounding for [bid/ask](https://twitter.com/kursatcalk/status/1686685226028666880) 

Please create [issues](https://github.com/beatzxbt/bybit-smm/issues) to flag bugs or suggest new features and feel free to create a [pull request](https://github.com/beatzxbt/bybit-smm/pulls) with any improvements.


If you have any questions or suggestions regarding the repo, or just want to have a chat, my handles are below 👇🏼

Twitter: [@beatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz
