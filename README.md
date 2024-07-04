Simple Market Maker
===================

This is a simple framework and set of strategies designed toward market making on crypto exchanges. 

***DISCLAIMER: Nothing in this repository constitutes financial advice (and therefore, please use at your own risk). It is tailored primarily for learning purposes, and is highly unlikely you will make profits trading any of the provided strategies. [BeatzXBT](https://twitter.com/BeatzXBT) will not accept liability for any loss or damage including, without limitation to, any loss of capital which may arise directly or indirectly from use of or reliance on this software.***

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

The account **must** be a Unified Trading Account (UTA).

_Optional: If you are using the testnet to trade, set the `TESTNET` flag to True within the `.env` file:_
```
TESTNET=True
```

### Install the requirements
_Optional: If you are familiar with virtual environments, create one now and activate it. If not, this step is not necessary:_

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

- `account_size` - Your account size in USD.
- `primary_data_feed` - Either Binance or Bybit. While most of the features are based on Bybit's own price, selecting Binance will start additional websocket streams to enable additional pricing features. Only possible if the symbol is trading on Binance USD-M.

- `binance_symbol`: - The derivatives symbol on Binance USD-M, unused if primary_data_feed is set to Bybit.
- `bybit_symbol`: - The derivatives symbol on Bybit Futures.

#### Master offsets 
- `price_offset` - Offset the generates quote prices ± some value. Positive number increases the quote price (and vice versa), however keep in mind that the API will return errors if the offset causes the minimum quote price to be less than 0, or the prices to be outside the exchange defined min/max range.
- `size_offset` - Offset the generates quote sizes ± some value. Positive number increases the quote size (and vice versa), however keep in mind that the API will return errors if the offset causes the minimum quote size to be less than minimum trading size.
- `volatility_offset` - Offset the total quote range ± some value (Positive number increases the distance between the lowest bid and the highest ask, and vice versa)


#### Market Maker Settings
Settings regarding the functionality of the core market making script
- `base_spread` - Lowest spread you're willing to quote at any given volatility. This may be scaled depending on the short-term volatility, up to 10x it's value.
- `min_order_size` - The minimum order size of the closest order to mid-price. 
- `max_order_size` - The maximum order size of the further order from mid-price. 
-  `inventory_extreme` - A value between 0 <-> 1, defining the maximum limit at which the system quotes normally. If inventory delta exceeds this value, it will stop quoting the opposite side and go into a reduce-only mode.

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

1. Prices from Bybit (and optionally Binance) are streamed using websockets into a common shared class.
2. Features are calculated from the updated market data, and a market maker class generates optimal quotes
  * Multiple features work on comparing different mid-prices to each other (trying to predict where price is likely to go).
  * Both bid/ask skew is then calculated, based on the feature values but corrected for the current inventory (filled position).
  * Prices & sizes are generated based on the skew, with edge cases for extreme inventory cases.
  * Spread is adjusted for volatility (as a multiple of the base spread), widening when short term movements increase.
  * Quotes are generated using all the above, formatted for the local client and returned.
3. Orders are sent via a Order Management System (currently disabled), which transitions between current and new states, and tries to do so in the most ratelimit-efficient way possible.
  

## Contributions

Please create [issues](https://github.com/beatzxbt/bybit-smm/issues) to flag bugs or suggest new features and feel free to create a [pull request](https://github.com/beatzxbt/bybit-smm/pulls) with any improvements.

## Contact

If you have any questions or suggestions regarding the framework/strategies, or just want to have a chat, my handles are below 👇🏼

Twitter: [@BeatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz


## Donations
If you want to support my open source work, please reach out to my Twitter (make sure its the correct account) and i will send an address of your preference. 

Others ways of supporting me are sign-up referral links for exchanges. At the moment, i'm a Bybit partner and can get a small part of your fees if you sign up using [this link](https://partner.bybit.com/b/beatz).
