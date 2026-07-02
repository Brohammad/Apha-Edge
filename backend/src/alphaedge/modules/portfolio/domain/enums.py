from enum import StrEnum


class RebalanceStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    EXECUTED = "executed"


class RiskLimitType(StrEnum):
    MAX_POSITION_PCT = "max_position_pct"
    MAX_DRAWDOWN = "max_drawdown"
    MAX_VAR = "max_var"
