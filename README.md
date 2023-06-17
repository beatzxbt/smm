Bybit Simple Market Maker
===================

This is a sample market making bot for use with [Bybit](https://www.bybit.com/en-US/).


Getting Started
---------------

1. Assuming you already have a Bybit account, generate API keys and secrets using [this guide](https://learn.bybit.com/bybit-guide/how-to-create-a-bybit-api-key/)
2. Swap your key/secret into the config file found in /config/bybit.yaml/
3. Install all packages required by running 'pip install -r requirements.txt' 
4. Adjust the contract settings in the parameters.yaml file (tick size/lot size) according to the symbol you want to make
5. Alter the spreads, order sizes, offsets (anything in the .yaml file!) as you wish, even whilst the bot is live!


Strategy
---------------

* It tracks mark price, and quotes both sides (range is defined by volatility, sizing by your preference)
  * The volatility indicator in use is simply adding the absolute(high-low) of x-candles in the past
  * The indicator can be found [here](https://www.tradingview.com/script/p5sEaH9V-Simple-Range-Volatility/) and contains a short explanation on how to manipulate it's parameters.
  * You can change these parameters once you're comfortable in the .yaml file 
* Under normal conditions, both sides have equal quote distances and sizing
* If too much inventory is accumulated (extreme value can be altered in the .yaml file), it will kill quotes on one side
* There is room to add bias by offsetting quote prices in the .yaml file


Fixes/Improvements
---------------

* Implementation of TWAP (func already exists in /src/bybit/orders/) to aid in reducing one-sided inventory
* Execption handling for orders (rate limits, high latency etc)
  

Upcoming features
---------------
* Option to add oscillating indiactors (RSI/Stoch) as a bias for pricing/sizing
* Binance market data integration, providing the option to track either Bybit's Mark Price, Binance Spot Price or a mixture of both
* Limit chasing TWAP
* Smart order submission (https://twitter.com/BeatzXBT/status/1668322708986163203)
* Easier integration of custom volatility indicators/metrics
