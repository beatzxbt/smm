Simple Market Maker
===================

This is a simple framework and set of strategies designed toward learning market making on crypto exchanges. 

***DISCLAIMER: Nothing in this repository constitutes financial advice (and therefore, please use at your own risk). It is tailored primarily for learning purposes, and is highly unlikely you will make profits trading any of the provided strategies. [BeatzXBT](https://twitter.com/BeatzXBT) will not accept liability for any loss or damage including, without limitation to, any loss of capital which may arise directly or indirectly from use of or reliance on this software.***

# Getting Started

### Clone the repository

In the terminal run the following commands:
```console
# Change directories to your workspace
$ cd /path/to/your/workspace

# Clone the repository
$ git clone git@github.com:beatzxbt/smm.git

# Change directories into the project
$ cd smm
```

__Note: Each terminal command going forward will be run within the main project directory.__

### Set Up the environment

Copy `.env.exmaple` to `.env`. This is where we are going to store our API keys:
```console 
$ cp .env.example .env
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

Sensible defaults are set in `smm/config.toml`. Edit this file to configure your venue,
symbol, trader, and component settings.

Key sections in the TOML file:
- `core` for venue, symbol, and trader selection
- `volatility` for EWMA settings and spread clamps
- `pricing` for levels, base spread, inventory limits, and spread ladder
- `risk` for max inventory and distance limits
- `oms` for create/amend/cancel rate budgets
- `plain` or `stinky` for trader-specific overrides

#### Running the bot

To run the bot, once your `.env` and `smm/config.toml` file are configured, simply run:
```console
(venv) $ python3 -m smm
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
  

## Roadmap

### Upcoming Applications

#### napalm
A specialized execution algorithm designed for large order placement across multiple exchanges. Napalm will handle the complexity of coordinating large positions across different venues, optimizing execution timing and exchange selection based on real-time market conditions.

#### cmm (Complex Market Maker)
A sophisticated market making framework that complements the simple market maker (smm). CMM removes the single-instrument and single-venue restrictions of SMM, enabling multi-venue, multi-instrument market making strategies under a unified strategy framework. This allows traders to run more complex market making operations with interconnected orders across multiple markets simultaneously.

#### glasses
A comprehensive monitoring and analytics platform that collects massive amounts of data from multiple exchanges via public streams. Glasses provides an interactive GUI for real-time visualization and interaction with live order books and market data. It optionally integrates with private data streams from smm and cmm instances, enabling extensive monitoring of trading operations, performance metrics, and market conditions all in one place.


## Contributions
Please create [issues](https://github.com/beatzxbt/bybit-smm/issues) to flag bugs or suggest new features and feel free to create a [pull request](https://github.com/beatzxbt/bybit-smm/pulls) with any improvements.


## Future ideas
- Data ingestion services to DB w/Dashboard, customized monitoring for markouts, risk limits, fills etc.
- Execution algorithms to enter large positions on single/combined exchanges (eg $1M BTC Long HL, $1M BTC Short Extended)

## Contact
If you have any questions or suggestions regarding the framework/strategies, or just want to have a chat, my handles are below 👇🏼

Twitter: [@BeatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz


## Donations
If you want to support my open source work, please reach out to my Twitter/Discord (make sure its the correct account) and i will send an address of your preference. 

Others ways of supporting me are sign-up referral links for exchanges. At the moment, i'm a Bybit partner and can get a small part of your fees if you sign up using [this link](https://partner.bybit.com/b/beatz).
