# Plain

abcd

Description
----------
This strategy uses an aggressiveness value to determine how powerful the price prediction features are in influencing the quote's skew.

When closer to the midprice, the best bid/ask tends to be the most filled quotes and such their prices/sizes are very inflencial in resultant PnL. In this case,

Step-by-Step Breakdown
----------
1. Set a base spread at a point considering fees & how volatile the market is.
2. abcd

TLDR
----------
- Quoting wide around a plain mid-price
- Place orders xBPS away from the mid, and a take profit at xBPS/2 in profit (long & short)
- Keep close eye on total exposure to avoid getting liquidated in a tail event.
- Avoid too many levels rate limits can hurt when you need them the most!


----------


# Stinky

This strategy aims to capture the strong mean reversion effect on deep fills.

Description
----------
We assume that mid-price is the fair price for our chosen asset, and we want to capture fills around this price.
However, rather than being competitive for the best bid/ask liquidity, we chose to quote unusually wide and capitalize
on the mean reverting nature of deep fills. There are multiple levels to try and capture as trades will rarely have identical impact each time.

Try identify markets which have abnormally thin liquidity relative to how much volume is being traded, using metrics such as xBPS bid/ask depth
relative to daily volume, and the market impact curve of large orders (you can spot this sometimes by watching the trades & orderbook feeds side-by-side).

Consider fees an major cost here, from experience it ends up being more than expected! In chosing the base levels, observe where price spiking commonly.
Is it hitting ~80BPS all of a sudden, then reverting 3/4ths of the way? Then probably place your order ~80BPS away from the mid, and your profit at 40BPS.
Remember, these orders *do* have a market impact that moves the price over time, however we're playing the quick mean reversion. Other fellow arboors are
taking the different price on your exchange, and hedging on a primary market (or everywhere else thats cheap for them to do so). They're usually the ones who
fill our orders.

Don't get greedy and place the take profit at <20BPS, you might not get filled and the position safety check will be forced to market out of the position
losing out on fees & potential profits. As distance from mid increases, our mean reversion effect grows stronger and such, we are incentivized to bet more size.
Maintain a low-ish exposure if you quote tight, as it can (again, from experience) sweep all your stink bids and go 2-3x deeper than you previously imagined.

This strategy is known to, and certainly will end up with a lot of left tail PnL. It's impossible to prevent this, as not all fills will mean revert & you'll be
left with bad inventory. The goal of the position checker at the end of each cycle (in this case, it is a fixed duration of the position) is precisely to exit
postitions if this mean reversion doesn't occur, to prevent liquidation-like losses in a tail event. However, in the long run, you get paid handsomely for the
'smaller' positions and likely will make more than your tail losses as time goes on.

Make sure to adjust your levels whenever needed, markets change and so should your interpretation of how asymetric trades behave.

Step-by-Step Breakdown
----------
1. Set a base spread at a point considering fees & how volatile the market is.
2.

TLDR
----------
- Quoting wide around a plain mid-price
- Place orders xBPS away from the mid, and a take profit at xBPS/2 in profit (long & short)
- Keep close eye on total exposure to avoid getting liquidated in a tail event.
- Avoid too many levels rate limits can hurt when you need them the most!