# Plain

## Overview

The 'Plain' strategy is a market-making algorithm designed to generate bid and ask quotes, to facilitate buying more on the bid side or selling more on the ask side, based on market conditions and skew predictions.

## Strategy Breakdown

### Components

1. **Corrected Skew**:
    - Adjusts the skew value to account for the current inventory. A higher net inventory leads to a higger correction in the skew to prevent overbuying/overselling.

2. **Corrected Spread**:
    - Ensures the spread is within acceptable bounds based on the minimum spread parameter. This adjustment helps maintain a consistent quoting behavior.

3. **Order Preparation**:
    - Generates bid and ask orders with specified prices and sizes. Orders are generated in a sequence prioritizing inner orders (closer to the mid-price) over outer orders.

### Methods

1. **corrected_skew(skew: float) -> float**:

    *Adjusts the skew value to account for the current inventory. It applies a negative correction to the skew if the inventory is long to prevent overbuying, and applies a positive correction to the skew if the inventory is short. This ensures the strategy maintains a roughly delta neutral inventory in the long term*
    - Adjusts the skew based on inventory delta.
    - Parameters:
        - `skew`: Original skew value.
    - Returns: Corrected skew value.

2. **corrected_spread(spread: float) -> float**:
    
    *Ensures the spread is within acceptable bounds based on a minimum spread parameter. This method clips the spread between the minimum spread and five times the minimum spread, providing stability in quoting behavior across different volatility regimes.*
    - Adjusts the spread to ensure it is within acceptable bounds.
    - Parameters:
        - `spread`: Original spread value.
    - Returns: Corrected spread value.

3. **prepare_orders(bid_prices: Array, bid_sizes: Array, ask_prices: Array, ask_sizes: Array) -> List[Order]**:

    *Generates bid and ask orders based on specified prices and sizes. It prioritizes inner orders (closer to the mid-price) over outer orders, ensuring the most competitive quotes are placed first. The method generates order IDs to comply with the Order Management System (OMS) specifications.*
    - Prepares bid and ask orders with specified prices and sizes.
    - Parameters:
        - `bid_prices`: Array of bid prices.
        - `bid_sizes`: Array of bid sizes.
        - `ask_prices`: Array of ask prices.
        - `ask_sizes`: Array of ask sizes.
    - Returns: List of prepared orders.

4. **generate_positive_skew_quotes(skew: float, spread: float) -> List[Order]**:

    *Creates orders with a positive skew, meaning it intends to fill more on the bid side (buying more) than on the ask side (selling less). It calculates the best bid and ask prices, generates geometric sequences for bid and ask prices, and computes sizes using a geometric weight distribution.*
    - Generates positively skewed bid/ask quotes.
    - Parameters:
        - `skew`: Value predicting the future price (should be > 0).
        - `spread`: Value in dollars representing the minimum price deviation.
    - Returns: List of orders reflecting positive skew.

5. **generate_negative_skew_quotes(skew: float, spread: float) -> List[Order]**:

    *Generates orders with a negative skew, intending to fill more on the ask side (selling more) than on the bid side (buying less). Similar to the positive skew method, it calculates the best bid and ask prices, generates geometric sequences for prices, and computes sizes using a geometric weight distribution.*
    - Generates negatively skewed bid/ask quotes.
    - Parameters:
        - `skew`: Value predicting the future price (between -1 and 1).
        - `spread`: Value in dollars representing the minimum price deviation.
    - Returns: List of orders reflecting negative skew.

6. **generate_orders(skew: float, spread: float) -> List[Order]**:

    *Determines whether to generate positive or negative skew quotes based on the skew value. It calls the appropriate method (`generate_positive_skew_quotes` or `generate_negative_skew_quotes`) to generate the orders.*
    - Determines whether to generate positive or negative skew quotes based on the skew value.
    - Parameters:
        - `skew`: Value predicting the future price.
        - `spread`: Value in dollars representing the minimum price deviation.
    - Returns: List of generated orders.


## Usage

To use the 'Plain' strategy, ensure that `quote_generator` is set to 'plain' in the `parameters.yaml` file [here](/smm/parameters.yaml).


# Stinky

## Overview

The 'Stinky' strategy aims to capitalize on the strong mean reversion effect observed in deep fills by placing bid and ask orders unusually wide and takes profits quickly.

## Strategy Breakdown

### Description

The core assumption of the 'Stinky' strategy is that the mid-price is the fair price for the chosen asset. Instead of being competitive for the best bid-ask liquidity, this strategy quotes wider to capture deep fills. It places multiple levels of orders to take advantage of the varying impact of trades.

#### Target Markets

- **Ideal Candidates**: Markets with abnormally thin liquidity relative to the volume being traded, such as meme coins (PEPE/WIF/TURBO/etc)
- **Less Effective**: Major assets with substantial liquidity (BTC/ETH/SOL/etc).

#### Fee Considerations

- Fees can be a significant cost, often more than anticipated.
- Ensure base levels and spreads account for fee structures (rule of thumb, minimum profit > 2.5x max costs).

#### Risk Management

- Maintain low exposure for tight quotes to avoid liquidation in volatile moves.
- Adjust base levels constantly based on market behavior and observed price spikes.

#### Tail Risk

- The strategy **will** be succeptable during significant price movements, resulting in heavy left-tail Pnl.
- Aim to profit from small positions frequently to offset occasional large losses.
- Concurrent safety checks in place to exit positions if mean reversion does not occur within the expected duration.

### Components

1. **Deep Order Generation**:
    - Generates orders in a range from the base spread to a spread raised to the power of 1.5 away from the mid-price.
    - Utilizes geometric spreads and sizes for bid and ask orders.

2. **Position Management**:
    - Monitors and purges positions exceeding a specified duration to prevent large losses.
    - Executes taker orders to exit positions if necessary.

### Methods

1. **generate_stinky_orders() -> List[Order]**:

    *Generates a series of bid and ask orders based on geometric spreads and sizes, ranging from the base spread to a spread raised to the power of 1.5.*
    - Returns: A list of orders.

2. **position_executor(max_duration: float=5.0) -> List[Union[Order, None]]**:

    *Checks if the current position's duration exceeds a specified maximum duration and generates a taker order to exit the position if necessary.*
    - Parameters:
        - `max_duration`: Maximum duration in seconds before purging the position.
    - Returns: A list containing either a single taker order or an empty list if no order is generated.

3. **generate_orders(fp_skew: float, vol: float) -> List[Order]**:

    *Combines the position executor and stinky order generation methods to create a comprehensive order generation process.*
    - Parameters:
        - `fp_skew`: Future price skew.
        - `vol`: Volatility.
    - Returns: A list of generated orders.

## Usage

To use the 'Stinky' strategy, ensure that `quote_generator` is set to 'stinky' in the `parameters.yaml` file [here](/smm/parameters.yaml).
