"""Honest analytics exposure classification helpers."""

from alphaedge.modules.analytics.presentation.router import _country_for_instrument


def test_country_from_exchange() -> None:
    assert _country_for_instrument("NSE", "INR", {}) == "IN"
    assert _country_for_instrument("NASDAQ", "USD", {}) == "US"


def test_country_from_metadata_wins() -> None:
    assert _country_for_instrument("NSE", "INR", {"country": "sg"}) == "SG"


def test_country_falls_back_to_unclassified() -> None:
    assert _country_for_instrument("UNKNOWN", "XYZ", {}) == "Unclassified"
