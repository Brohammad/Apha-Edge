# Broker integrations

## Supported brokers

| Broker | Status | Notes |
|--------|--------|-------|
| Paper | Live | Simulated fills |
| Alpaca | Live | US equities REST API |
| IBKR | Stub | Requires TWS/IB Gateway |

## IBKR setup (future)

1. Run IB Gateway or Trader Workstation locally
2. Enable API connections on configured port (default 7497 paper / 7496 live)
3. Create broker connection with `account_id`, `host`, `port`

## Adding a broker

1. Add `BrokerName` enum value
2. Add credential schema in `execution/domain/credentials.py`
3. Implement `BrokerPort` adapter
4. Register factory in `execution/infrastructure/registry.py`
5. Add frontend form in `BrokerConnectionModal`
