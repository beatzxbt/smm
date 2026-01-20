# Traders

This folder contains the runnable trader implementations and their components
(pricing, risk, OMS). Each trader is configured through `smm/config.toml`.

## Plain

**Intent:** Simple mid-price following market maker with lightweight settings.

**Behavior:**
- Quotes symmetric levels around the mid price.
- Spreads widen with volatility and with inventory utilization.
- Level 0 on the inventory-adding side is reduced as inventory grows.

**Key Config Sections:**
- `[pricing]` for levels, base spread, inventory limits, and spread ladder.
- `[volatility]` for EWMA settings and spread clamps.
- `[risk]` for max inventory and distance limits.
- `[oms]` for rate budgets.
- `[plain]` for plain-specific overrides.

## Stinky

**Intent:** Wide, linear quote ladders aimed at capturing deep fills.

**Behavior:**
- Linear spacing between `min_spread_bps` and `max_spread_bps`.
- Market-order liquidation after a configurable wait.

**Key Config Sections:**
- `[stinky]` for spreads, levels, and liquidation thresholds.
- `[pricing]`, `[risk]`, `[oms]`, `[volatility]` for shared behavior.
