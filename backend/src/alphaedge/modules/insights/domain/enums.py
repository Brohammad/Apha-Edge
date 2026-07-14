from enum import StrEnum


class InsightType(StrEnum):
    STRATEGY_EXPLANATION = "strategy_explanation"
    PERFORMANCE_REPORT = "performance_report"
    RISK_INTERPRETATION = "risk_interpretation"
    TRADE_SUMMARY = "trade_summary"
    COMPANY_RESEARCH = "company_research"
    INSIDER_INTELLIGENCE = "insider_intelligence"
    STRATEGY_LOSS_ANALYSIS = "strategy_loss_analysis"


class SourceType(StrEnum):
    STRATEGY = "strategy"
    STRATEGY_VERSION = "strategy_version"
    BACKTEST = "backtest"
    PORTFOLIO = "portfolio"
    RISK_SNAPSHOT = "risk_snapshot"
    ORDER = "order"
    INSTRUMENT = "instrument"
    SEC_FILING = "sec_filing"


class InsightStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
