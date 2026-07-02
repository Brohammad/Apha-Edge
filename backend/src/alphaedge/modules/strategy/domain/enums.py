from enum import StrEnum


class StrategyType(StrEnum):
    PYTHON = "python"
    DSL = "dsl"


class VersionStatus(StrEnum):
    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"


class SignalAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
