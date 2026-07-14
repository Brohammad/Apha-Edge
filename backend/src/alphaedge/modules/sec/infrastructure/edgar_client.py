"""SEC EDGAR API client."""

from __future__ import annotations

import httpx

from alphaedge.config import settings


class EdgarClient:
    BASE_URL = "https://data.sec.gov"

    def __init__(self, user_agent: str | None = None) -> None:
        self._user_agent = user_agent or settings.sec_user_agent

    async def fetch_submissions(self, cik: str) -> dict:
        cik_padded = cik.zfill(10)
        url = f"{self.BASE_URL}/submissions/CIK{cik_padded}.json"
        headers = {"User-Agent": self._user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_filing_document(self, url: str) -> str:
        headers = {"User-Agent": self._user_agent}
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.text
