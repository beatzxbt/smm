# Exchange Interface (Framework)

Generally in a trading system, there are three steps
Here is where the code is written for two 



## Architecture Overview

The framework is built around a modular architecture with clear separation of concerns:

### Base Classes

#### `BaseExchange`
The core exchange interface that provides:
- **Order Management**: Create, amend, and cancel orders with unified parameters
- **Account Operations**: Position and balance monitoring
- **Client Management**: REST and WebSocket client lifecycle management
- **Error Handling**: Standardized error propagation and retry logic
- **Rate Limiting**: Built-in protection against API rate limits

#### `BaseMarketData`
Handles real-time market data streaming:
- **Multi-Symbol Support**: Concurrent data streams for multiple trading pairs
- **Data Normalization**: Converts exchange-specific formats to common structures
- **Broadcasting**: Distributes data to multiple consumer queues
- **Reconnection Logic**: Automatic reconnection with exponential backoff
- **Message Routing**: Topic-based message handling for different data types

#### `BasePrivateData`
Manages private data streams:
- **Authentication**: Secure WebSocket authentication for private channels
- **Order Updates**: Real-time order status and execution notifications
- **Position Tracking**: Live position and balance updates
- **Account Events**: Account-level notifications and changes

### Internal Data Structures

The framework uses standardized internal structures to maintain consistency across exchanges:

- **`TickerMsg`**: Price and volume snapshots
- **`OrderbookMsg`**: Bid/ask depth data
- **`TradeMsg`**: Public trade executions
- **`OrderMsg`**: Order status and lifecycle events
- **`ExecutionMsg`**: Trade execution details
- **`PositionMsg`**: Position size and PnL updates
- **`AccountMsg`**: Account balance and margin information

### Design Philosophy

The framework balances **implementation specificity** with **interface uniformity**. While each exchange has unique characteristics and API quirks, the framework abstracts these differences behind common data structures and method signatures. This approach provides:

- **Strategy Simplicity**: Trading strategies work with consistent data formats regardless of the underlying exchange
- **Exchange Optimization**: Each exchange implementation can leverage native features and optimizations
- **Maintainability**: Clear separation between exchange-specific logic and common functionality
- **Extensibility**: New exchanges can be added by implementing the base interfaces

## Supported Exchanges

### OKX
- **Margin Mode**: Cross margin only
- **Order Types**: Market and limit orders with various time-in-force options
- **Authentication**: API key, secret, and passphrase required

### Bybit
- **Account Type**: Unified Trading Account (UTA) only
- **Margin Mode**: Cross margin only
- **Order Types**: Market, limit, and conditional orders
- **Authentication**: API key and secret authentication

## Getting Started

Each exchange implementation follows the same pattern:

1. **Initialize the exchange client** with API credentials
2. **Set up market data streams** for required symbols
3. **Configure private data feeds** for order and position updates
4. **Implement strategy logic** using the unified data structures

The framework handles all the low-level details of connection management, authentication, and data normalization, allowing you to focus on trading logic.

