# Interview Talking Points — AlphaEdge

Five stories to tell in 2–3 minutes each. Each follows **situation → decision → tradeoff → outcome**.

---

## 1. Modular monolith with bounded contexts

**Situation:** A trading platform spans auth, strategies, backtests, execution, risk, and market data — easy to turn into a distributed mess.

**Decision:** Single deployable FastAPI app with 19 bounded contexts (`identity`, `strategy`, `execution`, …), each with `domain → application → infrastructure → presentation`.

**Tradeoff:** More folders than a flat MVC app; no microservice independence.

**Outcome:** One `docker compose up` runs the full stack; teams can own a context without cross-repo coordination. ~232 Python modules, clear dependency direction.

**If they dig deeper:** Show `backend/src/alphaedge/modules/strategy/` layer split vs `analytics` router that bypasses application layer (known inconsistency).

---

## 2. DSL compiler + dual runtime (YAML + Python)

**Situation:** Quants want YAML for simple rules and Python for custom indicators.

**Decision:** Custom DSL parser + AST validator for Python; shared `StrategyRuntime` for backtests and live paper deployments.

**Tradeoff:** Python runs via `exec()` with restricted imports — not a true sandbox.

**Outcome:** DSL crossover strategies backtest in seconds; Python strategies support `StrategyBase` with injected indicators. C++ accelerator hits **~12M events/sec** on core path vs **~154K events/sec** Python (1M-bar benchmark).

**Sound bite:** "I built a compiler pipeline, not just a script runner."

---

## 3. Pre-trade risk gate on every order path

**Situation:** Orders can come from the API or from strategy deployments — risk checks must not be bypassable.

**Decision:** `RiskGate.evaluate()` as a single domain service: position sizing → exposure → cash/MIS margin → sell-without-holding → drawdown/VaR → daily loss.

**Tradeoff:** Uses latest daily bar close as price estimate — no real-time quote feed.

**Outcome:** 8 dedicated unit tests + integration tests; rejected orders return `RISK_REJECTED` with stage name, no stack traces.

**Sound bite:** "Same gate for manual clicks and automated signals."

---

## 4. Idempotent order execution

**Situation:** Celery retries and bar re-ingestion can submit duplicate orders.

**Decision:** DB unique constraint on `idempotency_key`; API accepts key in body; deployments use deterministic keys `deploy:{id}:{instrument}:{bar}:{side}`.

**Tradeoff:** No HTTP `Idempotency-Key` header yet — JSON body only.

**Outcome:** Safe retries without double fills; integration test covers deployment bar → signal → order.

---

## 5. Auth evolution: Bearer → cookies + WS tickets

**Situation:** SPA needed secure OAuth without tokens in the URL; WebSockets can't send cookies the same way as REST.

**Decision:** HTTP-only cookies for web login; `POST /auth/ws-ticket` issues single-use Redis tickets for WebSocket `Sec-WebSocket-Protocol`.

**Tradeoff:** Rate-limit tier resolution still reads Bearer/API key — cookie-only users get IP-based limits.

**Outcome:** OAuth redirect is `?oauth=success` only; production WS auth documented in security audit.

---

## Quick stats to memorize

| Metric | Value |
|--------|-------|
| Automated tests | 144 |
| Unit test coverage | ~58% |
| Backend modules | 19 bounded contexts |
| API routes | 63+ |
| C++ backtest speedup | ~78× vs Python (core path) |
| Stack | FastAPI, Celery, Postgres, Redis, React 19 |

---

## Questions you should ask them

1. "How do you handle pre-trade risk in production?"
2. "What's your approach to running user-submitted code?"
3. "How do you test async job pipelines end-to-end?"

These map directly to AlphaEdge's hardest problems.
