"""MIS (intraday) margin estimation for Indian product types."""

from __future__ import annotations

from decimal import Decimal

from alphaedge.modules.execution.domain.enums import ProductType

# SEBI-style simplified margin: ~20% of notional for equity MIS intraday.
DEFAULT_MIS_MARGIN_PCT = Decimal("0.20")
DEFAULT_NRML_MARGIN_PCT = Decimal("0.50")


def estimate_required_margin(
    *,
    notional: Decimal,
    product_type: ProductType,
) -> Decimal:
    """Return estimated margin blocked for an order notional."""
    if product_type == ProductType.MIS:
        return (notional * DEFAULT_MIS_MARGIN_PCT).quantize(Decimal("0.01"))
    if product_type == ProductType.NRML:
        return (notional * DEFAULT_NRML_MARGIN_PCT).quantize(Decimal("0.01"))
    return notional.quantize(Decimal("0.01"))
