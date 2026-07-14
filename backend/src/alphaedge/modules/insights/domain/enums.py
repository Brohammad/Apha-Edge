from enum import StrEnum


class InsightType(StrEnum):
    STRATEGY_EXPLANATION = "strategy_explanation"
    PERFORMANCE_REPORT = "performance_report"
    RISK_INTERPRETATION = "risk_interpretation"
    TRADE_SUMMARY = "trade_summary"
    COMPANY_RESEARCH = "company_research"


class SourceType(StrEnum):
    STRATEGY = "strategy"
    STRATEGY_VERSION = "strategy_version"
    BACKTEST = "backtest"
    PORTFOLIO = "portfolio"
    RISK_SNAPSHOT = "risk_snapshot"
    ORDER = "order"
    INSTRUMENT = "instrument"


class InsightStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
