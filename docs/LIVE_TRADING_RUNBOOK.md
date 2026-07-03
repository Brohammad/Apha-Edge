# Live Trading Production Runbook

This guide covers enabling real-money order routing through Alpaca on a production AlphaEdge deployment.

## Prerequisites

- [ ] Security audit completed (`docs/security/SECURITY_AUDIT.md`)
- [ ] Penetration test passed
- [ ] Alpaca live account funded and API keys issued
- [ ] `LIVE_TRADING_ENABLED=false` during staging validation

## Environment variables

```bash
# Required for live routing
LIVE_TRADING_ENABLED=true
ALPACA_API_KEY=...
ALPACA_API_SECRET=...
ALPACA_LIVE_BASE_URL=https://api.alpaca.markets

# Paper trading (recommended for staging)
ALPACA_PAPER_BASE_URL=https://paper-api.alpaca.markets
```

## Rollout steps

1. **Deploy with live trading disabled** — verify health, metrics, and paper order flow.
2. **Create Alpaca paper connection** via Orders → Connect Alpaca (paper) in the UI.
3. **Validate end-to-end** — submit paper orders, confirm fills and portfolio updates.
4. **Enable live trading** — set `LIVE_TRADING_ENABLED=true` and redeploy the API.
5. **Create live portfolio** — `is_paper=false` portfolio required for live orders.
6. **Connect Alpaca live** — provide per-user API credentials via broker connection.
7. **Place first live order** — UI requires explicit acknowledgment checkbox.

## Safety guards

The API enforces:

- `LIVE_TRADING_ENABLED` must be `true` for non-paper broker connections and orders
- Live orders require `live_trading_acknowledged: true` in the submit body
- Live orders cannot target paper portfolios
- Rate limiting applies to all authenticated endpoints

## Monitoring

- Grafana dashboard: `infrastructure/grafana/dashboards/alphaedge-api.json`
- Watch `http_requests_total` 4xx/5xx rates on `/orders` and `/broker-connections`
- Alert on order `rejected` status spikes

## Rollback

Set `LIVE_TRADING_ENABLED=false` and redeploy. Existing live connections remain stored but new live orders are rejected.
