from dataclasses import dataclass

from alphaedge.modules.insights.domain.enums import InsightType

PROMPT_VERSION = "v1"

PROMPT_TEMPLATES: dict[InsightType, dict[str, str]] = {
    InsightType.STRATEGY_EXPLANATION: {
        "v1": (
            "You are a quantitative trading analyst. "
            "Explain the following strategy in plain language.\n\n"
            "Strategy name: {strategy_name}\n"
            "Strategy type: {strategy_type}\n"
            "Parameters: {parameters}\n\n"
            "Source code / DSL:\n```\n{source_code}\n```\n\n"
            "Provide:\n"
            "1. A one-paragraph overview\n"
            "2. Entry and exit logic\n"
            "3. Key parameters and their effect\n"
            "4. Potential strengths and weaknesses"
        ),
    },
    InsightType.PERFORMANCE_REPORT: {
        "v1": (
            "You are a portfolio analyst. Write a performance report based on this backtest.\n\n"
            "Backtest: {backtest_name}\n"
            "Period: {start_date} to {end_date}\n\n"
            "Metrics:\n"
            "- Total return: {total_return}\n"
            "- Sharpe ratio: {sharpe_ratio}\n"
            "- Max drawdown: {max_drawdown}\n"
            "- Win rate: {win_rate}\n"
            "- Total trades: {total_trades}\n\n"
            "Equity curve summary: {equity_summary}\n\n"
            "Provide a structured Markdown report with executive summary, "
            "metrics analysis, and recommendations."
        ),
    },
    InsightType.RISK_INTERPRETATION: {
        "v1": (
            "You are a risk manager. Interpret this portfolio risk snapshot in plain language.\n\n"
            "Portfolio ID: {portfolio_id}\n"
            "Snapshot at: {snapshot_at}\n\n"
            "Risk metrics:\n"
            "- VaR 95%: {var_95}\n"
            "- VaR 99%: {var_99}\n"
            "- Max drawdown: {max_drawdown}\n"
            "- Sharpe: {sharpe_ratio}\n"
            "- Beta: {beta}\n"
            "- Alpha: {alpha}\n"
            "- Volatility: {volatility}\n\n"
            "Explain the risk profile, notable exposures, and suggested monitoring actions."
        ),
    },
    InsightType.TRADE_SUMMARY: {
        "v1": (
            "You are a trading desk analyst. Summarize the following trades.\n\n"
            "Source: {source_label}\n"
            "Total trades: {trade_count}\n\n"
            "Trades:\n{trades_text}\n\n"
            "Provide a narrative summary covering patterns, win/loss distribution, "
            "and notable trades."
        ),
    },
    InsightType.COMPANY_RESEARCH: {
        "v1": (
            "You are an equity research analyst. Synthesize company research.\n\n"
            "Symbol: {symbol}\n"
            "Company: {name}\n"
            "Exchange: {exchange}\n\n"
            "Web research summary:\n{research_summary}\n\n"
            "Sources: {research_sources}\n\n"
            "Provide investment-relevant highlights, risks, and recent developments."
        ),
    },
}


def get_prompt(insight_type: InsightType, version: str = PROMPT_VERSION) -> str:
    versions = PROMPT_TEMPLATES.get(insight_type)
    if not versions or version not in versions:
        raise ValueError(f"No prompt template for {insight_type.value}@{version}")
    return versions[version]


def render_prompt(template: str, context: dict[str, object]) -> str:
    return template.format(**{k: str(v) for k, v in context.items()})


@dataclass(frozen=True)
class LLMResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int
    completion_tokens: int
