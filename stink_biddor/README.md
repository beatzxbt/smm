# Stink Biddor 

This is a *simpler and dumber* take on a market making algorithm. 


## Strategy Design/Overview

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

This strategy is known to, and certainly will end up with a lot of left tail PnL. It's impossible to prevent this, as not all fills will mean revert & you'll be 
left with bad inventory. The goal of the position checker at the end of each cycle is precisely to exit postitions if this mean reversion doesn't occur, to prevent
liquidation-like losses in a tail event. However, in the long run, you get paid handsomely for the 'smaller' positions and *should* make more than your tail losses
as time goes on. Make sure to adjust your levels whenever needed, markets change and so should your interpretation of how asymetric trades behave.

## TLDR
- Quoting very wide around plain mid-price 
- Place orders xBPS away from the mid, and a take profit a few BPS in profit (long & short)
- Keep close eye on maintainance margin, never exceeding ~25% if all levels filled
- Avoid too many levels on either side, rate limits can hurt!
  
## NOTE
This system will **not** be included open source anytime soon, however people are of course free to modify the smm into something that works with these wide fills. Thats how my original stinkbiddor was formed!

## Contact

If you have any questions or suggestions regarding the strategy, or just want to have a chat, my handles are below 👇🏼

Twitter: [@beatzXBT](https://twitter.com/BeatzXBT) | Discord: gamingbeatz
