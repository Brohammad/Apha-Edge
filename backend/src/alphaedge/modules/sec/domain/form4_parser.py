"""Form 4 insider transaction parser (XML subset)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Form4Transaction:
    reporting_owner: str
    issuer: str
    transaction_date: str
    transaction_code: str
    shares: Decimal
    price: Decimal | None
    acquired_disposed: str  # A | D


class Form4Parser:
    """Parse key fields from Form 4 XML filings."""

    @classmethod
    def parse(cls, xml_text: str) -> list[Form4Transaction]:
        transactions: list[Form4Transaction] = []
        owner = cls._tag(xml_text, "rptOwnerName") or "Unknown"
        issuer = cls._tag(xml_text, "issuerName") or "Unknown"
        blocks = re.findall(r"<nonDerivativeTransaction>.*?</nonDerivativeTransaction>", xml_text, re.S)
        for block in blocks:
            date = cls._tag(block, "transactionDate") or ""
            code = cls._tag(block, "transactionCode") or ""
            shares = Decimal(cls._tag(block, "transactionShares") or "0")
            price_raw = cls._tag(block, "transactionPricePerShare")
            price = Decimal(price_raw) if price_raw else None
            ad = cls._tag(block, "transactionAcquiredDisposedCode") or "A"
            transactions.append(
                Form4Transaction(
                    reporting_owner=owner,
                    issuer=issuer,
                    transaction_date=date,
                    transaction_code=code,
                    shares=shares,
                    price=price,
                    acquired_disposed=ad,
                )
            )
        return transactions

    @staticmethod
    def _tag(text: str, tag: str) -> str | None:
        match = re.search(rf"<{tag}[^>]*>([^<]+)</{tag}>", text)
        return match.group(1).strip() if match else None
