"""Tavily web research provider."""

from __future__ import annotations

import httpx

from alphaedge.config import settings
from alphaedge.modules.insights.domain.research import ResearchProvider, ResearchResult
from alphaedge.shared.domain.exceptions import ValidationError


class TavilyResearchProvider(ResearchProvider):
    BASE_URL = "https://api.tavily.com/search"

    async def search(self, query: str, *, max_results: int = 5) -> ResearchResult:
        if not settings.tavily_api_key:
            return ResearchResult(
                query=query,
                summary=f"[offline] No Tavily key configured. Query: {query}",
                sources=[],
            )

        payload = {
            "api_key": settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "include_answer": True,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.BASE_URL, json=payload)
            if response.status_code >= 400:
                raise ValidationError(f"Tavily API error: {response.text[:500]}")
            data = response.json()

        sources = [
            {"title": r.get("title", ""), "url": r.get("url", "")}
            for r in data.get("results", [])
        ]
        return ResearchResult(
            query=query,
            summary=data.get("answer") or data.get("response", ""),
            sources=sources,
        )


class MockResearchProvider(ResearchProvider):
    async def search(self, query: str, *, max_results: int = 5) -> ResearchResult:
        return ResearchResult(
            query=query,
            summary=f"Mock research summary for: {query}",
            sources=[{"title": "Example Source", "url": "https://example.com"}],
        )


def get_research_provider() -> ResearchProvider:
    if settings.research_provider == "tavily":
        return TavilyResearchProvider()
    return MockResearchProvider()
