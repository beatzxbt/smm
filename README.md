Bybit Simple Market Maker
===================

This is a sample market making bot for [Bybit](https://www.bybit.com/en/).


Disclaimer
---------------

Nothing in this repository is financial advice for obvious reasons, it is primarily for learning purposes, it is highly unlikely you will make money trading this strategy and is meant as a stepping stone for your own MM systems. Feel free to copy pasta this repository and spin it off as your own personal MM, adding features and/or quote generators (or whatever you want honestly, but if you feel it can be improved without leaking much alpha then please do help everyone else by submitting a PR!)


Getting Started
---------------

NOTE: I have tested this with Python 3.11.7, i recommend you use a similar version (likely any 3.9 <-> 3.11 should do)

1. Assuming you already have a Bybit account, generate an API key/secret using [this guide](https://learn.bybit.com/bybit-guide/how-to-create-a-bybit-api-key/).
2. Swap your key/secret into the config file found in /config/bybit.yaml/
3. Install all packages required by running 'pip install -r requirements.txt' into the terminal.
4. Input the contract details in the parameters.yaml file (tick size/lot size) according to the symbol you want to make.
5. Alter the market maker parameters, offsets, symbols (any setting in the .yaml file) as you wish, even whilst the bot is live!

NOTE: Changing the primary data feeds or symbols will require a restart to the script


Strategy Design/Overview
---------------

1. Prices from Bybit (and optionally Binance) are streamed using websockets into a common shared class
2. Features are calculated from the updated market data, and a market maker class generates optimal quotes
  * Multiple features work on comparing different mid-prices to each other (trying to predict where price is likely to go).
  * Both bid/ask skew is then calculated, based on the feature values but corrected for the current inventory (filled position).
  * Prices & sizes are generated based on the skew, with edge cases for extreme inventory cases.
  * Spread is adjusted for volatility (as a multiple of the base spread), widening when short term movements increase.
  * Quotes are generated using all the above, formatted for the local client and returned
3. Orders are sent via a Order Management System (currently disabled), which transitions between current and new states, and tries to do so in the most ratelimit-efficient way possible.
  

New upgrades/add-ons
---------------

- Extensively documented codebase, with beginner friendliness as a priority


Current known bugs
---------------

- None so far (If any are encountered, please DM me on Twitter/Discord)


Improvements/Additions
---------------

- None planned for this repository in its current state, although i'm working on a major upgrade in [this branch](https://github.com/beatzxbt/bybit-smm/tree/v.2.0-alpha). It is faster, has a exchange-agnostic framework and supports multi-symbol execution. However, this is still very much WIP and will not work out of the box, so explore it only for learning purposes (or to take bits and bobs for your own system)!

---------------

If you have any questions or suggestions regarding the repo, or just want to have a chat, my handles are below 👇🏼

Twitter: [@beatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz

---------------

Also if you want to buy me a coffee (much appreciated :D), my addresses is below:

USDC: 0x84a16e23c38f84709395720b08348d86883acf81 (Arbitrum)
USDC: 9mJw3Wyifr19vqHJp6SLK86sDXrE6Ayk96U7F4Wano2H (Solana)
ETH: 0x84a16e23c38f84709395720b08348d86883acf81 (ERC20)