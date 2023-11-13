Stink Biddor 
===================

This is a *simpler and dumber* take on a market making algorithm. 


Getting Started
---------------

1. Make sure you have read the primary README.md in the main folder and followed its instructions (API info, sharedstate folders etc)
2. Open /smm/stink_biddor/settings.py to access your strategy specific settings, and add your exchange, symbol & price/size levels (explanation below)


Strategy Design/Overview
---------------

We assume that mid-price is the fair price for our chosen asset, and we want to capture fills around this price. However, rather than being competitive 
for the L1 liquidity, we chose to quote *abnormally* wide and capitalize on the mean reverting nature of deep fills. There are multiple levels to try and
capture, as these fills are produced by randomly-large sized orders. Try identify markets which have abnormally thin liqudity, using metrics such as 200BPS 
bid/ask depth relative to daily volume, and the market impact of large orders (you can spot this by watching the trades & orderbook feeds side-by-side).
Set your levels according to the market impact you're spotting. Is price spiking 80BPS all of a sudden, then reverting 3/4ths of the way? Place your order
75BPS away from the mid, and your profit at 40BPS. Remember, these orders *do* have a market impact that moves the price over time, however we're playing the 
quick mean reversion. Other fellow arboors are market ordering the different price on your exchange, and hedging on the primary market. So use them to fill our 
orders. Don't get greedy and place the take profit at <20BPS, you might not get filled and the position safety check will be forced to market out of the position
losing out on fees & potential profits. As distance from mid increases, our mean reversion effect grows stronger and such, we bet more size. Do keep an eye on your
total exposure on one size, as it should *never* be higher than 50% maintainance margin of exposure on the account. 

**TLDR**
-> Quoting very wide around mid-price 
-> Place orders xBPS away from the mid, and a take profit a few BPS in profit (long/short)
-> Keep close eye on maintainance margin, never exceeding 50%
-> Avoid more than 4 levels per side to account for rate limits
  

New upgrades
---------------

- None so far


Current known bugs
---------------

- High latency (>1000ms) will result in repeated 'no order found' errors
  -> Increase order refresh time from 1s -> 2x your latency to fix


Improvements/Additions Required
---------------

- Improving quote design to run position checker for fill per order, not the set of orders as a whole
  

---------------

If you have any questions or suggestions regarding the strategy, or just want to have a chat, my handles are below 👇🏼

Twitter: [@beatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz
