from alphaedge.modules.insights.domain.enums import InsightType
from alphaedge.modules.insights.infrastructure.mock_content import generate_mock_content


def test_empty_strategy_explains_no_signals():
    content = generate_mock_content(
        InsightType.STRATEGY_EXPLANATION,
        {
            "strategy_name": "Premium Alpha (clone)",
            "strategy_type": "dsl",
            "parameters": {},
            "source_code": "name: paid\nsignals: []\n",
        },
    )
    assert "no trading signals" in content.lower()
    assert "signals: []" in content


def test_strategy_with_rules_lists_entries():
    dsl = """
name: sma_crossover
parameters:
  fast_period: 10
signals:
  - when: crossover(sma(fast_period), sma(slow_period))
    then: BUY
"""
    content = generate_mock_content(
        InsightType.STRATEGY_EXPLANATION,
        {
            "strategy_name": "SMA Cross",
            "strategy_type": "dsl",
            "parameters": {"fast_period": 10},
            "source_code": dsl,
        },
    )
    assert "**BUY**" in content
    assert "crossover" in content
