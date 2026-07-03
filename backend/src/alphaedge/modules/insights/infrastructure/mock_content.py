"""Deterministic insight bodies for dev/CI when no LLM API key is configured."""

from __future__ import annotations

import re
from typing import Any

from alphaedge.modules.insights.domain.enums import InsightType


def _signal_rules(source_code: str) -> list[str]:
    return re.findall(r"^\s*-\s*when:\s*(.+?)\s*\n\s*then:\s*(\w+)", source_code, re.MULTILINE)


def _has_empty_signals(source_code: str) -> bool:
    if re.search(r"signals:\s*\[\s*\]", source_code):
        return True
    return len(_signal_rules(source_code)) == 0 and "signals:" in source_code


def strategy_explanation(context: dict[str, Any]) -> str:
    name = str(context.get("strategy_name", "Unknown"))
    strategy_type = str(context.get("strategy_type", "unknown"))
    parameters = context.get("parameters") or {}
    source_code = str(context.get("source_code", "")).strip()
    rules = _signal_rules(source_code)

    if _has_empty_signals(source_code):
        return f"""# Strategy insight: {name}

## Overview

**{name}** is a `{strategy_type}` strategy with **no trading signals defined**. In its current form it will not generate buy or sell orders during backtests or live execution — it is effectively a placeholder.

## Entry and exit logic

- **Entry:** None. The DSL declares `signals: []`, so no conditions trigger a position.
- **Exit:** None. Without entries, there is nothing to close.

If this was cloned from a marketplace listing, the published source may be intentionally minimal until purchase/unlock. Edit the strategy and add signal rules before expecting trades.

## Key parameters

Parameters: `{parameters}`

With no signals referencing parameters, changing values has **no effect** on behavior today.

## Strengths and weaknesses

**Strengths**
- Safe default — cannot accidentally place trades.
- Easy starting point to add your own rules.

**Weaknesses**
- **Not tradeable** as-is; backtests will show zero activity.
- No edge, risk controls, or position sizing until signals are added.
"""

    rule_lines = "\n".join(f"- **{action}** when `{condition}`" for condition, action in rules)
    param_lines = (
        "\n".join(f"- `{key}` = {value}" for key, value in parameters.items())
        if parameters
        else "- No parameters declared."
    )

    return f"""# Strategy insight: {name}

## Overview

**{name}** is a `{strategy_type}` strategy with **{len(rules)} signal rule(s)**. It reacts to indicator conditions on each bar and emits buy/sell actions when rules fire.

## Entry and exit logic

{rule_lines}

Typical pattern: **BUY** rules open or add exposure; **SELL** rules reduce or flatten. Exact sizing depends on portfolio and execution settings outside the DSL.

## Key parameters

{param_lines}

Tuning lookback periods or thresholds in these parameters shifts how sensitive the indicators are and how often signals fire.

## Strengths and weaknesses

**Strengths**
- Rule-based logic is explicit and easy to audit.
- Parameters can be optimized without rewriting code.

**Weaknesses**
- Indicator crossovers can whipsaw in ranging markets.
- No built-in stop-loss or position limits in the DSL snippet alone — validate risk in backtests.
"""


def performance_report(context: dict[str, Any]) -> str:
    name = str(context.get("backtest_name", "Backtest"))
    total_return = context.get("total_return", "N/A")
    sharpe = context.get("sharpe_ratio", "N/A")
    max_dd = context.get("max_drawdown", "N/A")
    win_rate = context.get("win_rate", "N/A")
    trades = context.get("total_trades", 0)
    equity = str(context.get("equity_summary", "N/A"))

    return f"""# Performance report: {name}

## Executive summary

Backtest **{name}** ({context.get("start_date")} → {context.get("end_date")}) finished with total return **{total_return}**, Sharpe **{sharpe}**, and max drawdown **{max_dd}** over **{trades}** trades.

## Metrics analysis

- **Equity path:** {equity}
- **Win rate:** {win_rate}
- Compare drawdown to return — high return with deep drawdown may be unacceptable for your risk budget.

## Recommendations

- Re-run with different date ranges to check robustness.
- Inspect individual trades for concentration in a few symbols or days.
- Consider slippage and fees if this was run with idealized fills.
"""


def risk_interpretation(context: dict[str, Any]) -> str:
    return f"""# Risk interpretation

## Risk profile

Portfolio `{context.get("portfolio_id")}` snapshot at **{context.get("snapshot_at")}**.

| Metric | Value |
|--------|-------|
| VaR 95% | {context.get("var_95")} |
| VaR 99% | {context.get("var_99")} |
| Max drawdown | {context.get("max_drawdown")} |
| Sharpe | {context.get("sharpe_ratio")} |
| Beta | {context.get("beta")} |
| Alpha | {context.get("alpha")} |
| Volatility | {context.get("volatility")} |

## Monitoring

- Watch VaR breaches versus realized P&L.
- Elevated beta implies more market sensitivity; size positions accordingly.
"""


def trade_summary(context: dict[str, Any]) -> str:
    source = str(context.get("source_label", "trades"))
    count = context.get("trade_count", 0)
    trades_text = str(context.get("trades_text", ""))

    return f"""# Trade summary: {source}

## Overview

**{count}** trade(s) in scope.

## Trade log (sample)

{trades_text}

## Patterns

Review win/loss clustering by symbol and session. Large outliers often dominate P&L — flag them for manual review.
"""


_GENERATORS = {
    InsightType.STRATEGY_EXPLANATION: strategy_explanation,
    InsightType.PERFORMANCE_REPORT: performance_report,
    InsightType.RISK_INTERPRETATION: risk_interpretation,
    InsightType.TRADE_SUMMARY: trade_summary,
}


def generate_mock_content(insight_type: InsightType, context: dict[str, Any]) -> str:
    generator = _GENERATORS.get(insight_type)
    if not generator:
        return f"# Insight\n\nMock report for `{insight_type.value}` (no template yet)."
    return generator(context)
